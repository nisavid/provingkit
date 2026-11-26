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

The trusted local UTF-8 JSON request has exactly these fields, and for a later
attempt also the pair described under reconciliation below:

- `message_id`, `attempt_id`, and `evidence_ref`: nonempty strings; the JSON-escaped attempt ID is limited to 256 characters by the source validator.
- `actor` and `recipient`: the identity objects above. The request recipient must equal the planned recipient. On the name path its `thread_id` must also equal `name`; otherwise the sender returns `recipient_name_mismatch` before any claim or listing.
- Exactly one address: `name`, the recipient's readable name as a `ListAgents` row
  prints it, optionally with `selection: {"ref": ...}` to check a
  single row's reference or choose among rows sharing the name; or `target`, a
  nonempty recipient-prepared `uds:` route for `SendMessage.to`.
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

The sender requires a by-name address to contain no CR or LF and to fit within
300 UTF-16 code units, even in a catalog without `to.allOf`. It applies the limit
to the address checked before listing and to any selection it offers. A supplied
route gets the same check when the catalog includes the recognized `allOf` pair.
Astral characters count as two code units. BMP characters and combining marks
each count as one. Existing request and control-frame bounds also apply.

A name request also requires exactly one `ListAgents` entry whose object schema has a string `cursor` property, no required properties, and `additionalProperties: false`; the sender calls it once with an empty arguments object. Without it the request records `unsupported_listagents` and no call is made.

Unknown dialects, altered or partial pattern pairs, extra constraints on supplied arguments, and unknown root constraints remain unsupported before the call. The sender compares literal constraint forms; it does not evaluate arbitrary patterns, resolve schemas, or validate a general schema. A recognized profile with an unmet destination constraint records `destination_constraint_violation`, a constraint diagnosis, and refusal before `tools/call` or possible submission. An unsupported profile retains `unsupported_sendmessage_schema`. Inspect those outcomes separately from submission.

Replies must be newline-delimited JSON-RPC objects with the expected integer ID and an object result, without an error member. Notification interleaving and other protocol variants are outside this parser's scope. Tool results support only text content items with exactly `type` and `text`, an optional Boolean `isError`, and optional object `_meta`. Other content shapes are unsupported. The JSON parsers do not provide strict duplicate-key or general non-finite-value rejection. These are compatibility gaps, not evidence that a receiver is incompatible. Broader support requires a reviewed source change and new evidence before use.

## Find the named recipient

A name request makes one `ListAgents` call before it can call `SendMessage`.
The entire response must match the observed Claude Desktop layout, including
the two blank lines. The names and references below are synthetic.

```text
This session is Fixture Origin [ab12ef] — the name other sessions use to message it (it is not listed below; a message to it would be a message to yourself).

Peer sessions (2):
  Fixture Team · Receiver [aa12bc]  ·  interactive  ·  idle  ·  Claude Desktop session  ·  started 8h ago
  Second Peer [bb34cd]  ·  interactive  ·  busy  ·  Claude Desktop session  ·  started 3h ago

[Cloud sessions and other computers are not listed because Remote Control is off in this session. The user can turn it on with the Remote Control switch in the app; then list again.]
```

The peer heading must declare the exact positive row count. Each row uses two
leading spaces, a name and a required six-digit lowercase hexadecimal
reference, `interactive`, `idle` or `busy`, `Claude Desktop session`, and
`started <age> ago`. The field separator is a middle dot with two spaces on
each side. A middle dot with single spaces can be part of a name. The caller
and row names must fit the name bounds and contain no field separators or
listing control text, including headings, footer text, and notices about
missing, hidden, or unreadable sessions.

The Claude Code 2.1.331 duration formatter in `mostSignificantOnly` mode
emits an integer with an `s`, `m`, `h`, or `d` suffix. The profile keeps
`0s` and positive integers of up to nine digits without zero padding. The
section count has the same nine-digit bound.

An altered, missing, or repeated part, extra line, unsupported row, other
section, note, empty-list form, title block, or pagination footer refuses the
entire listing before any `SendMessage` call. A layout or count failure records
`listing_incomplete`, and a heading, row, or label outside the profile records
`unrecognized_listing`. A row reusing the caller's reference also records
`listing_incomplete`. The caller's own name and a selection of the caller's
reference record `self_destination`. A `ListAgents`
call that fails or runs out of time, errs, or returns another result shape
records `listing_failed`, `listing_error`, or `unsupported_listing_result`,
respectively.

In a row with the complete observed form and a valid reference, a title
containing a square bracket or starting with `(` is unreadable. The sender
skips it only when its first field, including the bracketed reference,
neither equals the requested name nor starts with the requested name
followed by a space and `[`. Otherwise it refuses the whole send as
`unrecognized_listing`. A shortened row or one missing its six-digit
reference is outside the form. Embedded control text and the caller's
reference cause refusal even on rows whose titles are unreadable.
Skipped rows count toward the peer total. Once listing begins,
`unreadable_rows` records how many rows were skipped, in the sender result
and in the possible-submission or `not_delivered` record. A refusal retains
only the skips already counted.

A name that matches no row records `no_matching_local_row`. If exactly one
local row carries the name, the sender uses that row's bare name. A selection
then checks the reference and leaves the address bare. With several rows
carrying the name, the sender requires a selection and builds `name [ref]`
from the selected row. It records `ambiguous_name` when no selection is
given. A selected reference that matches no row for that name records
`selection_not_in_listing`, and one that matches more than one records
`ambiguous_selection`; a reference from an earlier attempt is
never reused, because each attempt starts its own child and lists again. For
`ambiguous_name`, `selection_not_in_listing`, and `ambiguous_selection`, the
result lists the matching rows in `candidates`. Each entry gives the `name`,
`ref`, `kind`, and whether the row is `local`. The result says
`needs: "selection"` when a local row has a reference no other matching row
shares and its qualified address fits the destination and call-frame limits.

Before listing, `prepare` and the sender check the bare frame without a
selection and the qualified frame with a selection. This budgets for a
second row appearing before send. The sender checks the actual frame again
after resolution. A 300-UTF-16-unit name fits the destination limit bare
and fails the pre-listing check with a reference. A 4,096-byte bare frame
fits the pipe limit, and `prepare` refuses the 4,105-byte qualified frame.

On the name path the planned recipient's `thread_id` is the name as the listing
prints it. That name is a label the recipient session chose, not a session
identifier, and nothing authenticates it: the equality binds the mailbox record
to the address, not to a session. The attempt's possible-submission record
keeps the row it addressed, with its name, reference, and kind. A row that alone
carries its name is addressed by the bare name; another session can take the
same name between the listing and the call, and what the tool does then is known
only from its description.

`prepare` and the sender both refuse a name the listing profile cannot read
as `invalid_name` before publication, claim, or listing. Names must fit within
300 UTF-16 code units and exclude unpaired surrogates, control characters,
line separators, surrounding whitespace, brackets, and the field separator.
A name cannot start with `(`, `<`, or `uds:`. The reserved name `main`
returns `self_destination` before publication, claim, or listing. The
recipient-prepared route is available for a session the name path cannot address.

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

After initialization and catalog inspection, the sender makes at most one `SendMessage` call, after the `ListAgents` reads of a name request. A missing tool, an unsupported schema, or a call frame over the 4,096-byte ceiling (`control_frame_limit`) records refusal without that call. Every refusal the sender records before possible submission is definite, on both paths: no `SendMessage` call was written in that attempt. It records `refused` with its reason and then `not_delivered`, whose evidence is the sender's own record of the phase. Before writing a supported call, it records possible submission on both paths as `phase`, `path`, and the `to` value, and for a name also the bound listing `row`. A supported non-error tool result records `submitted`; errors, malformed replies, unsupported results, interrupted writes, and other uncertain outcomes do not establish nondelivery. Inspect the returned JSON and retained observations; the process exit code alone does not establish successful submission.

`submitted` reports the tool result, not receiver receipt, ACK, handling, or fulfillment. The tool's own description says a successful call puts the message in the recipient's inbox, not read yet; report it as submission. The child ends after the call, so a later cross-session delivery notice has no process to reach. That limits this sender, not what is intended: the [skill entry](../SKILL.md) states the operator's 2026-11-19 decision that Claude's requested reply starts a turn in a Codex sender's chat while its app is running, with the mechanism still to be chosen. An ACK needs correlated receiver evidence and its meaning must be stated. Record receipt, handling, and completion only from separately acquired authorized evidence tied to the intended receiver, message, and attempt. Preserve contradictions and uncertainty; do not infer fulfillment from envelope serialization or sender success.

The sender counts stderr but discards its bytes. It buffers stdout for protocol parsing and stores selected request/result details, not a complete transcript. Retain the returned result and actual evidence behind `evidence_ref`; a pointer alone proves nothing. Bound and protect any separately authorized capture. Even a complete capture within its limits cannot prove absence outside those limits, on other channels, or in the receiver.

## Closure and reconciliation

The sender shuts its child down as the MCP 2024-11-05 stdio lifecycle describes. It closes the child's input and drains the pipes for up to three seconds within the remaining deadline. If the child has not exited, it sends `SIGTERM` and drains the pipes for two more seconds, so a child that writes while it stops is not blocked on a full pipe, then sends `SIGKILL`; these signal waits and reaping can pass the deadline. It waits for the child's own exit, not for its pipes to close, so a descendant that holds them does not extend the close. It reaps only the child it created. Inspect `owned_child`: `closed_by` is `terminate` or `kill` when a signal ended the child, and `closure_error` names a pipe or closure failure.

The fixed sender's close against a real session is not yet observed. Child closure does not establish receiver shutdown, descendant closure, or total process-tree control. A closure failure does not erase an earlier submission observation.

After uncertainty or interruption, inspect the same mailbox and reconcile through separately authorized receiver observations. A bounded history with no match is not conclusive nondelivery. Preserve claims, evidence, original sender, actual actor, owner, and holds across replacement intake. Do not automatically resend, start a fallback, change settings, or release a hold.

Mailbox bookkeeping permits a later claim only when it names the latest attempt, every earlier attempt ended `not_delivered`, and none shows receipt, handling, or completion. A later attempt is a new attempt ID under the same message identity, made only when the caller asks for it: the request then carries both `after_attempt` (the latest attempt) and `decision_ref` (the owning task's decision for this attempt), and the sender passes them to the claim unchanged. One without the other returns `invalid_reconciliation` before any claim. After a refused name send, for example, the caller supplies the missing `selection` from the refusal's `candidates` with both fields; the new attempt lists again and checks the selection against its own listing. The sender never starts a later attempt itself. An attempt that recorded possible submission ends in the sender's own record as `submitted` or `unknown`, never `not_delivered`, so no later attempt follows it through the sender; that needs nondelivery reconciled from the receiver's side, as [mailbox bookkeeping](native-codex-mailbox.md) says. Preclaiming does not bridge the gap, and a new message identity for the same obligation is not a later attempt.

## Consumer completion and compatibility

Keep compatibility claims graduated: reviewed source and parser checks; synthetic consumers at the real sender CLI with replaced external effects; separately authorized exact-surface negotiation; correlated receiver receipt; handling and fulfillment; installation and operational adoption. Passing one stage does not establish the next. Claude product surfaces require separate qualification.

Before completing source delivery, obtain current owning validation, independent review, and consumer evidence on the final revision and relevant dependencies. Exercise discovery separately from procedure application. Consumer cases should distinguish legacy and explicit correlation, original sender and forwarding actor, retained authority and holds, claimed-attempt refusal, supported submission, relevant protocol failures, limits, and owned-child closure. Synthetic evidence must identify the actual module exercised, replacements, source revision, commands, results, and assurance limits; it cannot qualify a live receiver.

A dependent consumer loads this procedure before execution and returns the reviewed revision, permitted route-binding evidence, mailbox/message/attempt bindings, actual actor, retained holds, bounded acquisition and observation limits, submission outcome, child closure, separately observed receiver stages, and unresolved gaps. Keep private evidence in its owning protected records. Changed source or evidence dependencies invalidate affected passes. Installation, adoption, and live acceptance remain with their existing owners.
