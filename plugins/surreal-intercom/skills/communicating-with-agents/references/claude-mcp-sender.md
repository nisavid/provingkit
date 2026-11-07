# Submit a peer message through a nominated Claude MCP child

Use this procedure under the owning task’s selected Claude-receiving native MCP route and applicable original or standing authority. Load this reference and record the reviewed source revision before dependent execution. [Peer binding and authority](peer-messages.md) governs the communication boundary; [mailbox bookkeeping](native-codex-mailbox.md) governs retained obligations and reconciliation.

The sender module is [scripts/claude_mcp_sender.py](../scripts/claude_mcp_sender.py). It uses [peer_message.py](../scripts/peer_message.py) to serialize a retained message and actual submitting actor. This is source support for a narrow stdio MCP profile. It establishes no installed release, live compatibility, authenticated grant, or native peer identity. Operational use, Claude startup, private-data disclosure, sending, installation, and adoption retain their separate gates.

## Bind inputs and authority

Use an existing, explicitly bound local SQLite mailbox with working locking. Preserve its path across replacement intake; never substitute an empty store for a missing recovery store. The store retains payloads, requests, targets, and tool results that may be private. Keep the store, journals, request files, and evidence under the owning task's protection and retention policy, outside committed source.

Plan an immutable message with `message_id`, `sender`, `recipient`, `owner`, `payload`, and `authority_ref`; supply the actual `holds`. Identities contain exactly `thread_id` and `host_id`. Preserve the original sender when forwarding; the submitting `actor` identifies the forwarding actor separately. `owner` retains responsibility for the message obligation; it does not identify the native endpoint’s process owner. Neither identity is authenticated by this module.

Give each distinct message a unique immutable `message_id`. Optional `correlation_id` links related messages in an exchange; it is not the duplicate-suppression identity. When omitted, the serializer uses `message_id` as the envelope correlation value without adding that field to the stored legacy message. Adding it later changes immutable content and is rejected for an existing identity. Preserve payload text, authority references, holds, and the referenced constraints transitively; serialization does not resolve or verify those references. Check the original grant, releases, recipient, actual actor, and retained holds before action. Existing verified grants, including their valid transitive scope, can cover ordinary calls; helper use alone does not require a fresh per-hop approval. Forwarding grants no new authority or ownership.

The trusted local UTF-8 JSON request has exactly these fields:

- `message_id`, `attempt_id`, and `evidence_ref`: nonempty strings; the JSON-escaped attempt ID is limited to 256 characters by the source validator.
- `actor` and `recipient`: the identity objects above. The request recipient must equal the planned recipient.
- `target`: a nonempty `uds:` nomination for `SendMessage.to`.
- `command`: a nonempty argument list whose executable path is absolute; the sender passes the exact argument vector with `shell=False`. An explicitly nominated launcher still has its own behavior and side effects.
- `limits`: exactly `operation_seconds`, `stdout_bytes`, and `stderr_bytes`, within the limits below.

The caller binds the executable, arguments, nominated endpoint, and intended receiver using separately permitted evidence. The retained request includes the command arguments; use the authorized environment-backed credential route rather than secret literals in those arguments. Matching the mailbox recipient does not prove that the endpoint reaches that recipient. A trusted request is a caller nomination, not proved binding, authentication, or permission. This module does not inspect receiver configuration, select an installed build, or verify startup side effects.

## Bounds and supported protocol

Request reading is capped at 32,769 bytes to reject files larger than 32,768 bytes. That read occurs before the operation deadline. The source does not restrict the request to a regular file or bound blocking open/read acquisition. Use a trusted prepared local file; do not claim a total invocation time bound. Mailbox acquisition and process creation also lack a complete wall-clock bound.

`operation_seconds` must be finite, greater than zero, and at most 60. One deadline covers protocol I/O and graceful child shutdown. Each stdout/stderr limit is an integer from 1 through 1,048,576 bytes for that invocation's pipe reads. The reader may consume one extra byte to detect overflow. Outgoing newline-delimited JSON control frames have a 4,096-byte ceiling, including the serialized envelope. This is a source-profile pipe-write ceiling, not a native peer message limit. Partial or failed writes remain uncertain.

The profile requests MCP `2024-11-05`, requires that returned protocol version and a tools capability object, then requests one complete `tools/list` catalog. A non-null continuation cursor is unsupported. It requires exactly one `SendMessage` entry when present. The supported schema profile requires an object with string `to` and `message` properties, exactly those required names, and `additionalProperties: false`. Root title/description annotations and property title/description/default annotations are accepted. The root `$schema` may be absent or exactly `https://json-schema.org/draft/2020-12/schema`; this recognizes a dialect annotation without implementing that dialect generally. Other optional properties may have object schemas and are not sent. Annotations never supply the destination or message.

The `to` property may additionally contain exactly this literal `allOf` pair, in the shown order:

```json
{"allOf": [{"pattern": "^[^\\n\\r]*$"}, {"pattern": "^[\\s\\S]{0,300}$"}]}
```

For this recognized profile, the sender checks the actual supplied target before recording possible submission: it must contain no CR or LF and at most 300 UTF-16 code units. Astral characters count as two code units; BMP characters and combining marks each count as one. This conservative source support limit does not claim general JSON Schema Unicode or regular-expression semantics. Without `to.allOf`, the legacy profile has no added destination constraint. Existing request and control-frame bounds still apply.

Unknown dialects, altered or partial pattern pairs, extra constraints on supplied arguments, and unknown root constraints remain unsupported before the call. The sender compares literal constraint forms; it does not evaluate arbitrary patterns, resolve schemas, or validate a general schema. A recognized profile with an unmet destination constraint records `destination_constraint_violation`, a constraint diagnosis, and refusal before `tools/call` or possible submission. An unsupported profile retains `unsupported_sendmessage_schema`. Inspect those outcomes separately from submission.

Replies must be newline-delimited JSON-RPC objects with the expected integer ID and an object result, without an error member. Notification interleaving and other protocol variants are outside this parser's scope. Tool results support only text content items with exactly `type` and `text`, an optional Boolean `isError`, and optional object `_meta`. Other content shapes are unsupported. The JSON parsers do not provide strict duplicate-key or general non-finite-value rejection. These are compatibility gaps, not evidence that a receiver is incompatible. Broader support requires a reviewed source change and new evidence before use.

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

After initialization and catalog inspection, the sender makes at most one `tools/call`. A missing tool or unsupported schema records refusal without that call. Before writing a supported call, it records possible submission. A supported non-error tool result records `submitted`; errors, malformed replies, unsupported results, interrupted writes, and other uncertain outcomes do not establish nondelivery. Inspect the returned JSON and retained observations; the process exit code alone does not establish successful submission.

`submitted` reports the tool result, not receiver receipt, ACK, handling, or fulfillment. An ACK needs correlated receiver evidence and its meaning must be stated. Record receipt, handling, and completion only from separately acquired authorized evidence tied to the intended receiver, message, and attempt. Preserve contradictions and uncertainty; do not infer fulfillment from envelope serialization or sender success.

The sender counts stderr but discards its bytes. It buffers stdout for protocol parsing and stores selected request/result details, not a complete transcript. Retain the returned result and actual evidence behind `evidence_ref`; a pointer alone proves nothing. Bound and protect any separately authorized capture. Even a complete capture within its limits cannot prove absence outside those limits, on other channels, or in the receiver.

## Closure and reconciliation

The sender closes stdin, drains its owned child's pipes within the remaining deadline, and waits. On closure failure it kills and reaps only the child it created; reaping can exceed the deadline. Inspect `owned_child` and any `closure_error`. Child closure does not establish receiver shutdown, descendant closure, or total process-tree control. A closure failure does not erase an earlier submission observation.

After refusal, uncertainty, or interruption, inspect the same mailbox and reconcile through separately authorized receiver observations. A bounded history with no match is not conclusive nondelivery. Preserve claims, evidence, original sender, actual actor, owner, and holds across replacement intake. Do not automatically resend, start a fallback, change settings, or release a hold.

Mailbox bookkeeping permits a later claim only after conclusive nondelivery reconciliation and an explicit owning-task decision, with every prior attempt satisfying its retained reconciliation conditions and no receipt, handling, or completion evidence. The sender request currently exposes neither `after_attempt` nor `decision_ref`; this sender cannot actuate that later-attempt route. Preclaiming does not bridge the gap. Return the need to the owning task rather than minting a new message identity or bypassing the claim.

## Consumer completion and compatibility

Keep compatibility claims graduated: reviewed source and parser checks; synthetic consumers at the real sender CLI with replaced external effects; separately authorized exact-surface negotiation; correlated receiver receipt; handling and fulfillment; installation and operational adoption. Passing one stage does not establish the next. Claude product surfaces require separate qualification.

Before completing source delivery, obtain current owning validation, independent review, and consumer evidence on the final revision and relevant dependencies. Exercise discovery separately from procedure application. Consumer cases should distinguish legacy and explicit correlation, original sender and forwarding actor, retained authority and holds, claimed-attempt refusal, supported submission, relevant protocol failures, limits, and owned-child closure. Synthetic evidence must identify the actual module exercised, replacements, source revision, commands, results, and assurance limits; it cannot qualify a live receiver.

A dependent consumer loads this procedure before execution and returns the reviewed revision, permitted route-binding evidence, mailbox/message/attempt bindings, actual actor, retained holds, bounded acquisition and observation limits, submission outcome, child closure, separately observed receiver stages, and unresolved gaps. Keep private evidence in its owning protected records. Changed source or evidence dependencies invalidate affected passes. Installation, adoption, and live acceptance remain with their existing owners.
