# Create And Use A Codex Daybreak Recipient

Use this procedure when an authorized operation needs a fresh local Codex
recipient and an explicitly selected Daybreak task, or needs to observe or
continue that retained operation. The native caller creates and reads the chat;
`scripts/codex_daybreak_sender.py` returns those caller controls and retains their
receipts. The helper submits the task through the discovered local owner.

This is a source procedure. Source and synthetic evidence establish only the
behavior they exercise; they do not establish installation, current app
compatibility, effective program/backend selection, or live delivery.

## Bind The Operation

Confirm permission to create the child and submit the task, the original sender,
submitting actor, obligation owner, payload, exchange correlation, and current
holds. The operation preserves those declarations; peer text and authority
references grant no additional authority. Rolecasting retains worker selection
and supervision. Keep original task obligations and their closure independent of
the harmless bootstrap, saved selection, submission, and connection closure.

Use a caller with native `mcp__codex_app__create_thread` and
`mcp__codex_app__read_thread` controls. Resolve the helper from this installed
skill. Select a private capture root and mailbox outside installed resources.
Use the existing capture policy and supply enough allowance for the operation's
retained evidence; `capture.run_root` must match `--root`. Initialize a new mailbox
through the [mailbox procedure](native-codex-mailbox.md) once, or retain the
selected existing mailbox; this helper does not replace its store.

An initial intent contains:

- Fresh nonempty `operation_id`, `message_id`, and `attempt_id`, plus
  `correlation_id` and `payload`.
- `sender`, `actor`, and `owner`, each exactly an object with nonempty `thread_id`
  and `host_id` strings.
- `authority_ref` and a `holds` list of nonempty references, which may be empty.
- The selected local IPC `endpoint`, external `mailbox`, `capture` settings, and
  numeric `observation_seconds` greater than zero and at most 10.

Use only the supported fields. A new recipient is bound from the native creation
receipt rather than supplied as an arbitrary target. Only local children are supported.
A remote child is refused before its binding is retained or a native read call
is returned. A caller must still verify its actual creation receipt and intended
local recipient; the helper does not authenticate that receipt.

The commands below use `$HELPER` for the installed helper and `$CAPTURE_ROOT` for
the selected private root. Input filenames stand for caller-retained JSON files.
The helper prints a JSON result; its `status`, references, and observed evidence
are the outcome, rather than the process exit code alone.

## Create And Observe The Bootstrap

1. Run `python -B "$HELPER" --root "$CAPTURE_ROOT" prepare --input intent.json`.
   Retain the result and its references. The first preparation returns
   `status: prepared` and `native_call`; preparation itself creates no native
   chat. Operation records live beneath the SHA-256 of `operation_id` in the
   capture root.
2. Execute that returned native call once through the actual caller. It requests
   `mcp__codex_app__create_thread` with `model: gpt-6-sol`,
   `target: {"type":"projectless"}`, and only the harmless prompt
   `Reply with Ready. Do not use tools or begin any other work.` This is a fresh,
   unforked ordinary bootstrap. The creation shape supplies no Daybreak or
   effort override. Retain the actual result; the shape alone proves no effective
   program or bootstrap outcome.
3. Run `python -B "$HELPER" --root "$CAPTURE_ROOT" bind OPERATION_ID --input creation.json`.
   Supply `call` equal to the retained creation call and the actual native
   `result`. Supply either `child: {"thread_id":"...","host_id":"local"}`
   or the unresolved native `client_thread_id`, never both. Retain the binding.
   For a failed or uncertain creation, also supply
   `creation: {"state":"unknown","evidence_ref":"..."}` (or state `failed`).
   Retain any actual child or pending handle; neither identifier is required
   when none was returned. This negative intake preserves the actual result and
   original operation references, returns no native call, and submits no task.
4. A bound child returns a caller-owned `native_call` for `read_thread` with its
   exact child identity, `turnLimit: 1`, `includeOutputs: false`, and
   `maxOutputCharsPerItem: 2048`. Execute that read only under the bound authority
   and retain the actual result. A queued creation remains `creation_pending`;
   use the pending branch below rather than creating a replacement.
5. Classify the actual bootstrap observation and run
   `python -B "$HELPER" --root "$CAPTURE_ROOT" submit OPERATION_ID --input bootstrap.json`.
   Supply the returned `call`, actual `result`, and
   `bootstrap: {"state":"completed","evidence_ref":"..."}` only when that
   evidence establishes completion. Otherwise retain `pending`, `failed`, or
   `unknown` with its evidence reference. These states retain uncertainty and do
   not submit the original task.
   A native read error (`result.isError`) permits only `unknown`: failure of the
   observation does not establish failure or completion of the bootstrap task.

The helper records caller-supplied observations; it does not execute native
creation/reads or independently interpret their results as completion proof.
Creation and bootstrap receipt envelopes reject undeclared fields, including
account, model, effort, and program requirements. The actual native `result`
remains opaque. Identical repeated intake returns retained state; conflicting
evidence refuses without replacing an earlier record.
The bootstrap carries no original task data. A completed bootstrap permits the
first task-submission attempt; it does not itself complete that task.

## Source Limits

The source profile allows at most 65,536 bytes in each incoming frame body,
262,144 incoming wire bytes, and 64 incoming events per connection. Each
serialized outgoing frame body is also limited to 65,536 bytes before any of that
frame is written. These are separate incoming and outgoing limits, not a total
bidirectional wire budget. A task-frame refusal can follow completed Daybreak
setup; retain that partial result and the original claim without replay.

`observation_seconds` governs each helper transport exchange, not the whole
operation, native creation, provider task, or later caller-owned read. Capture
settings constrain the controlled retained writes they describe; they are not
overall memory, elapsed-time, provider-cost, or app-write caps.

## Submit The Explicit Task

On the first completed-bootstrap intake, the helper claims the logical operation
before effects and claims its mailbox attempt. It discovers the local child's
owner, captures and sends `thread-follower-update-daybreak`, requires a matching
successful response with `ok: true`, then reads model settings and requires
`daybreakEnabled: true` before task submission.

Each explicit task request carries `model: gpt-6-sol`, `effort: medium`, and
`cyberAccessProgram: daybreakBlue`. Its default collaboration settings also carry
`gpt-6-sol` and `reasoning_effort: medium`. The retained `setup_ref` and
`attempt_ref` identify the setup and task envelopes; readback and selection
records preserve the saved-selection observation. A matching successful start
response with a turn ID yields `status: turn_accepted` and `turn_id`.

`turn_accepted` establishes the correlated accepted turn only. `receipt`,
`task_completion`, and `effective_program` remain unknown until evidence supports
their separate claims. Saved `daybreakEnabled` and a requested per-turn program
are separate observations; neither establishes the effective backend. Inspect
`owned_connection` and retained transport/failure records for actual closure.
They describe the helper-owned IPC connection, not child chat or task closure.

### Standing Admission At The Task Write

Use this route only for a host and caller already accepted for standing
admission. Record `"resource_admission":"standing-v1"` in the task intent and
pass `--standing-binding "$BINDING" --standing-eligible` before the subcommand
that can first submit it. This applies to completed bootstrap intake, pending
bootstrap reconciliation, and an explicitly authorized continuation. Use
`--standing-paused` or `--standing-independent-hold` when either condition
applies. The caller still checks the actor, task authority, and any independent
hold.

Supply an absolute binding path from trusted host configuration. The binding
must be a regular file owned by the helper's user, with mode `0600`. It holds
absolute `reader`, `authority_dir`, and `state_dir` paths and the accepted
`grant_id`. The reader must be a regular file owned by the same user, with
group and other write bits clear. The helper rejects symbolic links at the
binding or reader file. A task payload or peer message cannot choose the
binding or eligibility flags.

An independently ineligible start or invalid binding retains the original
operation claim and refusal before opening its mailbox or socket. After a valid
settings readback and task frame check, the helper rechecks the reader identity
and requests a current decision. Only a complete `routine-standing-decision/v1`
`ALLOW` with the bound grant and a runtime ID permits the task frame write.
A known refusal before the task write records `task_write: not_attempted`. If
setup ran, retain its saved selection and observed connection closure as
separate facts. A later eligible decision does not reopen the original attempt.
A continuation from a standing-admission operation must retain this mode.

## Reconcile Without Replay

Use `python -B "$HELPER" --root "$CAPTURE_ROOT" show OPERATION_ID` to inspect retained
state. Read-only inspection returns no new native call. An already claimed
operation is not resubmitted by repeating its command. After interruption or a
lost response, retain the original operation and attempt; `submission_unknown`
is an uncertainty barrier, not permission to retry the task.

- **Pending creation:** obtain native evidence resolving the same
  `client_thread_id`. Run `reconcile OPERATION_ID --input creation-resolution.json`
  with the original `call`, matching `client_thread_id`, resolved local `child`,
  actual `result`, and a nonempty `evidence_ref`. A valid first resolution returns
  the child's bootstrap read call. Preserve an unresolved handle without
  replacement creation. A negative observation of the same handle instead
  supplies the original `call`, matching `client_thread_id`, actual `result`,
  and `creation` classification/evidence as above. It retains
  `creation_outcome_ref` and returns no native call. Fresh evidence may later
  resolve that same uncertain handle; a retained failed outcome is terminal.
- **Pending bootstrap:** after a fresh native observation establishes completion,
  run `reconcile OPERATION_ID --input bootstrap-completion.json` with the original
  read `call`, actual `result`, and `bootstrap.state: completed` plus a fresh
  `bootstrap.evidence_ref`. This branch applies to a retained `pending` bootstrap.
  Its first completion intake may enter the original one-attempt submission;
  repeated completion intake returns retained state. A failed or unknown
  bootstrap has no automatic restart route. A fresh failed or unknown observation
  of that same pending bootstrap uses the same receipt shape and retains
  `bootstrap_outcome_ref` without a task or native call. A read-control error
  must be classified unknown. Fresh completion evidence for an uncertain
  pending bootstrap preserves that earlier outcome; a failed outcome is terminal.
- **Accepted task:** request one observation by running
  `reconcile OPERATION_ID --input task-wait.json`. Its input is exactly
  `{"task_wait":{"observation_seconds":10,"after_ref":null}}` for the first
  observation. The helper retains the request and returns one caller-owned native
  read. The duration records the caller's chosen observation budget;
  this helper starts no timed waiter and does not cap native tool latency or
  cancel an in-flight call. Use the caller's actual bounded observation controls
  without inventing timeout arguments. Retain pending references when the
  observation cannot be performed, and preserve unknown original-call closure.
- **Task read result:** run `reconcile OPERATION_ID --input task-observation.json`
  with exactly `task_wait_ref`, the returned `call`, actual native `result`, and
  `task: {"attempt_id":"...","turn_id":"...","state":"pending","evidence_ref":"..."}`.
  Bind both IDs to the retained accepted attempt. Supported task states are
  `pending`, `completed`, `failed`, and `unknown`; an error result requires
  `unknown`. Advance a claim only from matching evidence, not from the desired
  state. A bounded read with outputs omitted is no general reply acquisition.
- **Another task observation:** only after retaining the prior observation as
  `pending` or `unknown`, request another bounded read with `after_ref` equal to
  its exact `task_observation_ref` and a fresh evidence reference for the next
  result. Preserve `task_wait_ref` while its result is missing. Repeating an
  existing wait request returns retained state without another native call.
  `completed` and `failed` end this observation chain.

Follow retained references rather than synthesizing filenames. Creation,
bootstrap, and task observations stay distinct. Unsupported or conflicting input
returns `status: refused`; preserve the original records and report the reason.
No phase promises automatic polling, wakeup, restart, resend, or cleanup.

## Continue On The Same Child

For a separately authorized next task, run
`python -B "$HELPER" --root "$CAPTURE_ROOT" continue --input continuation-intent.json`.
Supply the full task intent, fresh `operation_id`, `message_id`, and `attempt_id`,
and `previous_operation_id` naming the retained predecessor. Reconfirm current
permission and holds; retain the original sender and obligation ownership rather
than treating the previous task as new authority.

The helper follows retained continuation links to the original local child and
completed bootstrap, records `continuation_ref`, and uses the same one-attempt
claim, saved-selection check, and explicit task request. It creates no new child
and replays no earlier task. A continuation does not discharge unresolved earlier
obligations. Reusing an existing operation ID returns retained state only when
its intent matches; conflicting intent is refused.

## Return The Observed Outcome

Return the operation/message/attempt references, bound child, retained status,
accepted turn ID if available, setup and task references, latest observation
references, evidence limits, actual owned connection closure, and the custodian
for pending obligations. Report original work completion only from its matching
task evidence. Keep source review, synthetic checks, installation, and live
qualification as separate acceptance records.
