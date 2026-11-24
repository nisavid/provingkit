# Submit a peer message through an owned Claude MCP child

Use this procedure for a message to a Claude agent under the applicable
original or standing authority. The ordinary first send to a local Claude agent
addresses it by name: the sender starts its own `claude mcp serve` child, finds
the name in that child's `ListAgents` listing, and makes one `SendMessage` call.
The recipient does nothing first. Prepare that request with the `prepare`
operation of [Claude route nomination](claude-route-nomination.md), which
resolves the caller's own `claude` launcher. A recipient-prepared `uds:` route
from the same procedure remains the fallback, used only when the request
supplies it. Do not ask the operator to supply a launcher, socket, request JSON,
or authority URI. Load this reference
and record the reviewed source revision before dependent execution. [Peer
binding and authority](peer-messages.md) governs the communication boundary;
[mailbox bookkeeping](native-codex-mailbox.md) governs retained obligations and
reconciliation.

The sender module is [scripts/claude_mcp_sender.py](../scripts/claude_mcp_sender.py). It uses [peer_message.py](../scripts/peer_message.py) to serialize a retained message and actual submitting actor. This is source support for a narrow stdio MCP profile. It establishes no installed release, live compatibility, authenticated grant, or native peer identity. Operational use, Claude startup, private-data disclosure, sending, installation, and adoption retain their separate gates.

## Bind inputs and authority

Use an existing, explicitly bound local SQLite mailbox with working locking. Preserve its path across replacement intake; never substitute an empty store for a missing recovery store. The store retains payloads, requests, targets, and tool results that may be private. Keep the store, journals, request files, and evidence under the owning task's protection and retention policy, outside committed source.

Plan an immutable message with `message_id`, `sender`, `recipient`, `owner`, `payload`, and `authority_ref`; supply the actual `holds`. Identities contain exactly `thread_id` and `host_id`. Preserve the original sender when forwarding; the submitting `actor` identifies the forwarding actor separately. `owner` retains responsibility for the message obligation; it does not identify the native endpoint’s process owner. Neither identity is authenticated by this module.

Give each distinct message a unique immutable `message_id`. Optional `correlation_id` links related messages in an exchange; it is not the duplicate-suppression identity. When omitted, the serializer uses `message_id` as the envelope correlation value without adding that field to the stored legacy message. Adding it later changes immutable content and is rejected for an existing identity. Preserve payload text, authority references, holds, and the referenced constraints transitively; serialization does not resolve or verify those references. Check the original grant, releases, recipient, actual actor, and retained holds before action. Existing verified grants, including their valid transitive scope, can cover ordinary calls; helper use alone does not require a fresh per-hop approval. Forwarding grants no new authority or ownership.

The trusted local UTF-8 JSON request has exactly these fields:

- `message_id`, `attempt_id`, and `evidence_ref`: nonempty strings; the JSON-escaped attempt ID is limited to 256 characters by the source validator.
- `actor` and `recipient`: the identity objects above. The request recipient must equal the planned recipient.
- Exactly one address: `name`, the recipient's name as a `ListAgents` row
  prints it (no brackets, CR, LF, or surrounding spaces, and no leading `uds:`,
  so a name is never sent as a route; at most 300 UTF-16 code units), optionally with `selection: {"ref": ...}` choosing one of
  several rows that share the name; or `target`, a nonempty recipient-prepared
  `uds:` route for `SendMessage.to`.
- `command`: a nonempty argument list whose executable path is absolute; the sender passes the exact argument vector with `shell=False`. An explicitly nominated launcher still has its own behavior and side effects.
- `limits`: exactly `operation_seconds`, `stdout_bytes`, and `stderr_bytes`, within the limits below.

The caller binds the executable, arguments, name or nominated endpoint, and
intended receiver using separately permitted evidence. Name preparation resolves
the caller's own `claude` launcher; route nomination obtains those transport
values from the selected receiver. Both preserve the launcher's invoked name.
A request that supplies a route is sent by that route, and the name path is not
tried for it. A name-only request that the name path refuses stays refused: the
sender does not look for a route itself, and no attempt follows a refusal with a
second path. The result's `path` says which was used. The retained request includes the command
arguments; use the authorized environment-backed credential route rather than
secret literals in those arguments. Matching the mailbox recipient does not
prove that the endpoint reaches that recipient. A trusted request is a caller
nomination, not proved binding, authentication, or permission. This module does
not inspect receiver configuration, select an installed build, or verify startup
side effects.

## Bounds and supported protocol

Request reading is capped at 32,769 bytes to reject files larger than 32,768 bytes. That read occurs before the operation deadline. The source does not restrict the request to a regular file or bound blocking open/read acquisition. Use a trusted prepared local file; do not claim a total invocation time bound. Mailbox acquisition and process creation also lack a complete wall-clock bound.

`operation_seconds` must be finite, greater than zero, and at most 60. One deadline covers protocol I/O and the wait after the child's input closes. Each stdout/stderr limit is an integer from 1 through 1,048,576 bytes for that invocation's pipe reads. The reader may consume one extra byte to detect overflow. Outgoing newline-delimited JSON control frames have a 4,096-byte ceiling, including the serialized envelope. This is a source-profile pipe-write ceiling, not a native peer message limit. Partial or failed writes remain uncertain.

The profile requests MCP `2024-11-05`, requires that returned protocol version and a tools capability object, then requests one complete `tools/list` catalog. A non-null continuation cursor is unsupported. It requires exactly one `SendMessage` entry when present. The supported schema profile requires an object with string `to` and `message` properties, exactly those required names, and `additionalProperties: false`. Root title/description annotations and property title/description/default annotations are accepted. The root `$schema` may be absent or exactly `https://json-schema.org/draft/2020-12/schema`; this recognizes a dialect annotation without implementing that dialect generally. Other optional properties may have object schemas and are not sent. Annotations never supply the destination or message.

The `to` property may additionally contain exactly this literal `allOf` pair, in the shown order:

```json
{"allOf": [{"pattern": "^[^\\n\\r]*$"}, {"pattern": "^[\\s\\S]{0,300}$"}]}
```

For this recognized profile, the sender checks the actual supplied target before recording possible submission: it must contain no CR or LF and at most 300 UTF-16 code units. Astral characters count as two code units; BMP characters and combining marks each count as one. This conservative source support limit does not claim general JSON Schema Unicode or regular-expression semantics. Without `to.allOf`, the legacy profile has no added destination constraint. Existing request and control-frame bounds still apply.

A name request also requires exactly one `ListAgents` entry whose object schema has a string `cursor` property, no required properties, and `additionalProperties: false`; the sender passes no argument but `cursor`. Without it the request records `unsupported_listagents` and no call is made.

Unknown dialects, altered or partial pattern pairs, extra constraints on supplied arguments, and unknown root constraints remain unsupported before the call. The sender compares literal constraint forms; it does not evaluate arbitrary patterns, resolve schemas, or validate a general schema. A recognized profile with an unmet destination constraint records `destination_constraint_violation`, a constraint diagnosis, and refusal before `tools/call` or possible submission. An unsupported profile retains `unsupported_sendmessage_schema`. Inspect those outcomes separately from submission.

Replies must be newline-delimited JSON-RPC objects with the expected integer ID and an object result, without an error member. Notification interleaving and other protocol variants are outside this parser's scope. Tool results support only text content items with exactly `type` and `text`, an optional Boolean `isError`, and optional object `_meta`. Other content shapes are unsupported. The JSON parsers do not provide strict duplicate-key or general non-finite-value rejection. These are compatibility gaps, not evidence that a receiver is incompatible. Broader support requires a reviewed source change and new evidence before use.

## Find the named recipient

A name request reads one `ListAgents` listing in the same attempt, following its
cursor to later pages, at most five, before any `SendMessage` call. Only a
session on this machine is addressed: a row in the listing's `Peer sessions`
section whose kind is `interactive`, `bg`, `daemon`, or `daemon-worker`. A row
for another machine, the cloud, or Remote Control is refused before the call
with `not_local_session`; widening that is the operator's decision. A name that
matches no row records `no_matching_local_row`. A name that matches more than
one row records `ambiguous_name` unless the request's `selection` names one of
them by the reference this attempt's listing shows; the call then addresses
`name [ref]` from that listing. A selection must match exactly one row: a
selected reference that this listing does not show records
`selection_not_in_listing`, and one it shows on more than one row records
`ambiguous_selection`; a reference from an earlier attempt is
never reused, because each attempt starts its own child and lists again. A
listing that reports missing, hidden, or failed rows, has a section whose rows
across all its pages differ in number from the total its header declares, or
does not end within five pages, records `listing_incomplete`; a row or other
line outside the profile records `unrecognized_listing`; a `ListAgents` call that fails or runs out of time, errs,
or returns another result shape records `listing_failed`, `listing_error`, or
`unsupported_listing_result`. Each refusal is recorded before any `SendMessage` call,
and the sender asks only for what is missing, such as the selection.

This listing profile, and the row kinds above, are read from the formatter in
the installed Claude Code 2.1.331 program, not from an observed listing. Outside
its sections, the profile has only the caller's own session line, the lines of
an empty listing, and the frame around a block of titles that people or other
sessions wrote. A different release can print differently; anything outside
the profile is refused, never guessed.

## Capture, submit once, and inspect

Resolve helpers from the reviewed skill resources. Prepare the message and request before invocation. The following invented local placeholders illustrate initial setup, planning, sender invocation, and inspection from a source checkout. They select no operational destination and grant no startup, disclosure, or sending authority. Run the sender line only after those gates are satisfied.

```sh
SKILL_DIR=plugins/surreal-intercom/skills/communicating-with-agents
python "$SKILL_DIR/scripts/native_codex_mailbox.py" --store ./example-private/mailbox.sqlite3 init
python "$SKILL_DIR/scripts/native_codex_mailbox.py" --store ./example-private/mailbox.sqlite3 plan --input ./example-private/message.json
python "$SKILL_DIR/scripts/claude_mcp_sender.py" --store ./example-private/mailbox.sqlite3 --request ./example-private/request.json
python "$SKILL_DIR/scripts/native_codex_mailbox.py" --store ./example-private/mailbox.sqlite3 show message-example
python "$SKILL_DIR/scripts/native_codex_mailbox.py" --store ./example-private/mailbox.sqlite3 pending
```

Use `init` only for authorized initial setup. The request's `message_id` must match the planned record; `message-example` is illustrative.

The sender acquires the claim itself. Do not preclaim through the mailbox CLI: an existing claim prevents the sender from proceeding. Before launching its child, it commits the attempt and an `unknown` observation containing the request. A crash can leave uncertainty before or after any external effect. Repeated invocation of that attempt cannot acquire another claim; a fresh attempt ID alone cannot reopen the message.

After initialization and catalog inspection, the sender makes at most one `SendMessage` call, after the `ListAgents` reads of a name request. A missing tool, an unsupported schema, or a call frame over the 4,096-byte ceiling (`control_frame_limit`) records refusal without that call. Before writing a supported call, it records possible submission on both paths as `phase`, `path`, and the `to` value, and for a name also the bound listing `row`. A supported non-error tool result records `submitted`; errors, malformed replies, unsupported results, interrupted writes, and other uncertain outcomes do not establish nondelivery. Inspect the returned JSON and retained observations; the process exit code alone does not establish successful submission.

`submitted` reports the tool result, not receiver receipt, ACK, handling, or fulfillment. The tool's own description says a successful call puts the message in the recipient's inbox, not read yet; report it as submission. The child ends after the call, so a later cross-session delivery notice has no process to reach. An ACK needs correlated receiver evidence and its meaning must be stated. Record receipt, handling, and completion only from separately acquired authorized evidence tied to the intended receiver, message, and attempt. Preserve contradictions and uncertainty; do not infer fulfillment from envelope serialization or sender success.

The sender counts stderr but discards its bytes. It buffers stdout for protocol parsing and stores selected request/result details, not a complete transcript. Retain the returned result and actual evidence behind `evidence_ref`; a pointer alone proves nothing. Bound and protect any separately authorized capture. Even a complete capture within its limits cannot prove absence outside those limits, on other channels, or in the receiver.

## Closure and reconciliation

The sender shuts its child down as the MCP 2024-11-05 stdio lifecycle describes. It closes the child's input and drains the pipes for up to three seconds within the remaining deadline. If the child has not exited, it sends `SIGTERM` and waits two more seconds, then sends `SIGKILL`; these signal waits and reaping can pass the deadline. It waits for the child's own exit, not for its pipes to close, so a descendant that holds them does not extend the close. It reaps only the child it created. Inspect `owned_child`: `closed_by` is `terminate` or `kill` when a signal ended the child, and `closure_error` names a pipe or closure failure.

The fixed sender's close against a real session is not yet observed. Child closure does not establish receiver shutdown, descendant closure, or total process-tree control. A closure failure does not erase an earlier submission observation.

After refusal, uncertainty, or interruption, inspect the same mailbox and reconcile through separately authorized receiver observations. A bounded history with no match is not conclusive nondelivery. Preserve claims, evidence, original sender, actual actor, owner, and holds across replacement intake. Do not automatically resend, start a fallback, change settings, or release a hold.

Mailbox bookkeeping permits a later claim only after conclusive nondelivery reconciliation and an explicit owning-task decision, with every prior attempt satisfying its retained reconciliation conditions and no receipt, handling, or completion evidence. The sender request currently exposes neither `after_attempt` nor `decision_ref`; this sender cannot actuate that later-attempt route. Preclaiming does not bridge the gap. Return the need to the owning task rather than minting a new message identity or bypassing the claim.

## Consumer completion and compatibility

Keep compatibility claims graduated: reviewed source and parser checks; synthetic consumers at the real sender CLI with replaced external effects; separately authorized exact-surface negotiation; correlated receiver receipt; handling and fulfillment; installation and operational adoption. Passing one stage does not establish the next. Claude product surfaces require separate qualification.

Before completing source delivery, obtain current owning validation, independent review, and consumer evidence on the final revision and relevant dependencies. Exercise discovery separately from procedure application. Consumer cases should distinguish legacy and explicit correlation, original sender and forwarding actor, retained authority and holds, claimed-attempt refusal, supported submission, relevant protocol failures, limits, and owned-child closure. Synthetic evidence must identify the actual module exercised, replacements, source revision, commands, results, and assurance limits; it cannot qualify a live receiver.

A dependent consumer loads this procedure before execution and returns the reviewed revision, permitted route-binding evidence, mailbox/message/attempt bindings, actual actor, retained holds, bounded acquisition and observation limits, submission outcome, child closure, separately observed receiver stages, and unresolved gaps. Keep private evidence in its owning protected records. Changed source or evidence dependencies invalidate affected passes. Installation, adoption, and live acceptance remain with their existing owners.
