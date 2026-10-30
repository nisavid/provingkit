# Recover native Codex message obligations

Use this Rolecasting procedure when Dispatch records an authorized native Codex
peer message, reconciles a sending result, or prepares replacement intake.
Load this document and record the source revision before dependent use.
The helper is [scripts/native_codex_mailbox.py](../scripts/native_codex_mailbox.py).
It keeps local obligations over existing native send/read/wait controls.
It does not provide a transport, an authority store, or a role assignment.

Dispatch setup owns acceptance on the real native path and operational cutover.
The predecessor Foreman remains the admission writer until the separately
accepted handover. Reading a mailbox transfers no operational ownership.

## Inputs and observation boundary

Use one explicitly bound SQLite store on a local filesystem with working SQLite
locking. Keep that same path available across process restarts and replacement
intake. Store placement, retention, and protection follow the owning task; the
store contains exact payloads and may contain private material. Do not commit
the operational store or its SQLite journal files.

A message is an immutable UTF-8 JSON object with these fields:

```json
{
  "message_id": "delivery-example",
  "sender": {"thread_id": "dispatch-example", "host_id": "local"},
  "recipient": {"thread_id": "worker-example", "host_id": "local"},
  "owner": {"thread_id": "foreman-example", "host_id": "local"},
  "payload": "[delivery-example] Intake only. Publication remains held.\n",
  "authority_ref": "synthetic://grant/intake-only",
  "holds": ["No operational transfer.", "Publication remains held."]
}
```

The example identities and pointers are synthetic. Bind real native host/thread
identities from the owning task. `sender` preserves the original captured author;
each attempt separately records its actual submitting `actor`. A replacement
Dispatcher uses its own actor identity without rewriting the original sender.
`owner` is the obligation's retained owner, not the process opening the store.
`authority_ref` points to the original grant; `holds` preserves the supplied hold
text. The caller checks the actual actor's routing, original grant, constraints,
releases, and holds before acting. A pointer or recorded assertion does not
authenticate, authorize, or transfer ownership.

`message_id` and `attempt_id` are caller-chosen nonempty strings. Keep them
stable; never mint a new identity merely to get around an existing claim.
Capture the complete original payload, including its correlation text. The
helper preserves the string without Unicode or newline normalization and
does not add a prefix. Native readback must correlate the actual recipient,
message, and attempt, using native identifiers and/or the recorded payload.
This store checks local identity associations; it does not verify readback.

The accepted offline boundary is the helper's CLI over a temporary real SQLite
store. Synthetic observations exercise recording and recovery; they do not
establish sender permission, native delivery, idle/busy behavior, approval
enforcement, recipient authenticity, effective model selection, or cutover.

## Capture, claim, and observe

Resolve `native_codex_mailbox.py` from this skill's `scripts/` resource directory.
In a source checkout it is
`plugins/rolecasting/skills/delegating-cross-agent-work/scripts/native_codex_mailbox.py`;
installed consumers use their resolved skill location. Bind that helper path
and reviewed source revision before use.

Choose the store path once. Only initial setup uses `init`; opening an existing
path with `init` fails, and other commands never create a missing store.
The following shell variable is an example local path, not a selected
operational destination:

```sh
MAILBOX_HELPER=/absolute/path/to/resolved/skill/scripts/native_codex_mailbox.py
MAILBOX_STORE=/absolute/path/to/dispatch-mailbox.sqlite3
python "$MAILBOX_HELPER" --store "$MAILBOX_STORE" init
python "$MAILBOX_HELPER" --store "$MAILBOX_STORE" plan --input message.json
```

`plan` returns `created: true` for a new identity and `created: false` for the
same immutable record. Reusing that identity with changed content is an error.
Omitting `holds` means an empty list; include the actual retained holds.

Before an external submission, persist a claim identifying the actual native
actor:

```sh
python "$MAILBOX_HELPER" --store "$MAILBOX_STORE" claim delivery-example attempt-example --actor-thread-id dispatch-example --actor-host-id local
```

A `claimed: true` result means this invocation created a new local claim for
this attempt. Commit happens before that result is printed. Only the caller
receiving that result may proceed to its separately authorized native send,
once. The attempt already records `unknown`: a crash may happen before or after
the native action. A claim is not a submission observation or permission to send.

`claimed: false` means that attempt identity is already claimed or that a new
attempt lacks the required reconciled basis. Stop sending and inspect the
retained record. A new attempt ID alone cannot reopen an obligation.
An attempt ID already bound to another message or a different actor is an
error. Transactions serialize concurrent claimers. The helper cannot stop an
external caller ignoring this result.

Record the observed sending result with its actual retained evidence pointer
and UTF-8 detail file:

```sh
python "$MAILBOX_HELPER" --store "$MAILBOX_STORE" observe delivery-example attempt-example submitted --evidence-ref evidence/send-result --detail-file send-result.txt
python "$MAILBOX_HELPER" --store "$MAILBOX_STORE" show delivery-example
```

Choose the observation kind from what was observed:

| Kind | Recorded distinction |
| --- | --- |
| `submitted` | A supplied result reports submission; receipt and handling remain separate. |
| `unknown` | Submission or its outcome remains uncertain, including an interrupted caller. |
| `refused` | A supplied result reports refusal, such as the retained idle-steer case. |
| `not_delivered` | Supplied conclusive evidence reports that this attempt did not deliver. |
| `received` | Supplied native receiver evidence correlates the message and attempt. |
| `handled` | Supplied evidence reports recipient handling. |
| `completed` | Supplied evidence reports completion of the requested action. |

Observations require the captured message and its claimed attempt, an evidence
pointer, and detail text. They are appended in local recording order. Detail
bytes must decode as UTF-8; text is retained without newline normalization.
The helper stores supplied observations, including contradictions. It neither
authenticates evidence nor decides which observation is justified. A bounded
history page with no match does not prove nondelivery.

The attempt's `submission` is the latest recorded submission/refusal/unknown
kind, initially `unknown`. Its separate `received`, `handled`, and `completed`
flags record only those explicit observations. Handling or completion does not
manufacture a receipt observation. A `not_delivered` observation preserves the
submission outcome and supplies a separately recorded reconciliation conclusion.
Attempts remain in claim order, and each retains its actor and observations.
A later attempt also retains `reconciliation` with `after_attempt`,
`nondelivery_ref`, and `decision_ref`; the first attempt has `reconciliation: null`.
The display `state` is the highest recorded processing stage across all attempts,
otherwise the latest attempt's submission outcome, otherwise `planned`.
A late lower-stage result cannot erase a recorded receipt, handling, or completion.
Inspect the full observations when facts conflict; the display is not an
adjudication.

## Reconciliation and replacement intake

After an uncertain send, use the existing authorized native `read_thread` and
`wait_threads` controls, retaining the relevant actual receiver/turn/message
identities and returned cursors. Paginate the relevant bounded history when
needed. Append the correlated observations; do not resend because a sending
result was lost or a bounded read found no match. This procedure adds no
polling schedule, timeout, automatic reader, or retry loop.

A replacement opens the same store and reads:

```sh
python "$MAILBOX_HELPER" --store "$MAILBOX_STORE" pending
python "$MAILBOX_HELPER" --store "$MAILBOX_STORE" show delivery-example
```

`pending` returns a consistent local snapshot, sorted by message ID. It includes
planned, unknown, refused, submitted, received, and handled messages until an
explicit completion observation is recorded. Original payloads, authority
pointers, owner identities, holds, attempts, and all observations remain
available. Completed messages stay retrievable through `show`.

Do not initialize a new empty store to stand in for a missing recovery store.
A replacement must preserve pending obligations and their uncertainty without
changing the owner or releasing holds. Intake is not accepted handover.
Check observation evidence and recover the original authority through its
existing owner before any later action.

A later submission for the same obligation requires conclusive nondelivery
reconciliation and an explicit owning-task decision. A bare `refused` or
`unknown` observation supplies neither. Record the evidence through the
existing observation command, then request a distinct attempt under the same
message identity:

```sh
python "$MAILBOX_HELPER" --store "$MAILBOX_STORE" observe delivery-example attempt-example not_delivered --evidence-ref evidence/conclusive-nondelivery --detail-file nondelivery.txt
python "$MAILBOX_HELPER" --store "$MAILBOX_STORE" claim delivery-example attempt-continuation --actor-thread-id replacement-example --actor-host-id local --after-attempt attempt-example --decision-ref decisions/owning-task-continuation
```

The caller establishes nondelivery and confirms that the original authority,
holds, actual actor, and recipient still permit the action. Evidence and
decision references are retained caller-supplied observations, not authenticated
permission. `--after-attempt` and `--decision-ref` must be supplied together.

A later claim succeeds only when it names the latest existing attempt, every
existing attempt's last observation is `not_delivered`, and no existing attempt
has any receipt, handling, or completion observation. Its `nondelivery_ref` is
bound to the latest attempt's last observation. Later uncertainty on any older
attempt blocks another claim until explicitly reconciled; a conflicting receipt
continues to block even if followed by a nondelivery assertion. A decision
reference alone cannot override these conditions. Original attempts and
observations remain unchanged. Duplicate calls for an existing attempt never
produce another successful claim.

There is no automatic retry, timer, backoff, transport action, reset, deletion,
retargeting, or ownership-transfer operation. A later successful claim still
requires its caller to perform the separately authorized native action, once.

## Verification and consumer handback

From the source checkout root, run the focused offline consumer suite after
applying the reviewed candidate:

```sh
python -m unittest discover -s tests/plugins -p 'test_rolecasting_native_mailbox.py'
git diff --check
```

The suite drives real CLI processes and temporary stores. It covers separate
delivery stages, idle-steer refusal as supplied evidence, uncertain-result
reconciliation, immutable duplicate capture, concurrent claimers, observation
identity mismatches, and replacement recovery with retained holds. It also
covers replacement actor binding, evidence-bound later attempts, blocking when
any prior attempt remains uncertain or has a conflicting receipt, and rejection
of a missing recovery store. It does not invoke native messaging.

Dispatch setup consumes this document and the reviewed source revision before
its real native checks. Its handback records that revision, the store binding,
offline test evidence, real permitted correlated delivery and idle-steer
observations, uncertain-result reconciliation, duplicate suppression, and
replacement intake with holds. Preserve any unavailable or unresolved result.
Only Dispatch's separately accepted native evidence and handover can establish
operational cutover; an offline pass establishes this bookkeeping interface.

There is no authentication, authority enforcement, content-based deduplication,
cross-store coordination, automatic evidence acquisition, or power-loss/storage
qualification in these tests. SQLite locking and the configured filesystem
bound local persistence. Schema version 1 has no migration facility; use a
retained compatible reviewed revision for an existing store.
