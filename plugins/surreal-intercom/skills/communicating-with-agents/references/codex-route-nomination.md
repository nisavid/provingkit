# Prepare A Guarded Codex Route

Use [codex_route_nomination.py](../scripts/codex_route_nomination.py) when a new
ordinary message targets an exact existing local Codex conversation and no bound
native send covers it. Reuse an unchanged nomination for the same authorized
submitter and recipient while its bindings remain valid. An already-held addressed reply stays on the
[native reply-forwarding route](native-peer-relay.md). The agent prepares the
route from its supported controls. Ask the operator only for an ambiguous
recipient, missing permission, or required intervention.

The same nomination is the supported return path when that Codex conversation
originates a message requesting a reply. Prepare and corroborate it before the
outbound submission, binding the outbound recipient as its return submitter.
It supplies return readiness for both reply-expected cases in the shared three-case reply/wait contract.
The current wait choice does not decide whether the nomination is prepared.
The immutable message's `reply_route` field carries only its safe path, size,
digest, completed native invocation, and original recipient, submitter, and
correlation bindings. It carries no endpoint and grants no permission. The
existing owner-admission consumer must still validate the private record,
invocation, permissions, peer identity, recipient, message authority, and holds.

## Construct The Reply Route

After the safe producer result is returned and the invocation is corroborated,
construct this exact `reply_route` field. Replace typed placeholders with the
actual producer result, original sender identity, outbound recipient identity,
exchange correlation, and corroborated invocation fields. The agent derives
these values from its controls; the operator does not assemble them.

<!-- reply-route-example:codex-owner-admission:start -->
```json
{
  "schema": "provingkit-peer-reply-route-v1",
  "kind": "codex-owner-admission",
  "recipient": {
    "thread_id": "$REPLY_RECIPIENT_THREAD_ID",
    "host_id": "$REPLY_RECIPIENT_HOST_ID"
  },
  "submitter": {
    "thread_id": "$REPLY_SUBMITTER_THREAD_ID",
    "host_id": "$REPLY_SUBMITTER_HOST_ID"
  },
  "correlation_id": "$CORRELATION_ID",
  "nomination": {
    "path": "$NOMINATION_PATH",
    "sha256": "$NOMINATION_SHA256",
    "size": "$NOMINATION_SIZE",
    "invocation": {
      "control": "native-read-thread-command-execution",
      "taskRef": "$INVOCATION_TASK_REF",
      "attemptId": "$INVOCATION_ATTEMPT_ID",
      "chat": {
        "thread_id": "$REPLY_RECIPIENT_THREAD_ID",
        "host_id": "$REPLY_RECIPIENT_HOST_ID"
      },
      "command": "$INVOCATION_COMMAND",
      "workingDirectory": "$INVOCATION_WORKING_DIRECTORY",
      "helper": {
        "path": "$INVOCATION_HELPER_PATH",
        "sha256": "$INVOCATION_HELPER_SHA256"
      },
      "evidenceRef": "$INVOCATION_EVIDENCE_REF",
      "nativeItemId": "$INVOCATION_NATIVE_ITEM_ID",
      "status": "completed",
      "exitCode": 0
    }
  }
}
```
<!-- reply-route-example:codex-owner-admission:end -->

Set `recipient` to the immutable message's original `sender`, `submitter` to its
outbound `recipient`, and `correlation_id` to its correlation ID (or message ID
when no separate correlation is present). Copy `path`, `sha256`, and `bytes` from
the safe producer result, using `bytes` as `size`. Copy the remaining invocation
values only from the trusted corroborated command item and its caller-owned
original invocation. Then pass the complete immutable message through the
mailbox planner; malformed or mismatched fields stop before planning.

## Bind The Acts And Selection

The producer request uses `codex-route-nomination-request-v2`. It binds the
recipient, actual Codex producer, submitting actor, acquisition `operationId`,
`acquisitionHolds`, three permission records, expected native invocation, source-qualified launch
and listener selection, and private publication destination. The producer is the
exact Codex recipient for this operation. The submitter may be a different actor,
such as Claude.

Bind each permission to the actor who performs the act:

- Metadata acquisition belongs to the Codex producer and is consumed by the
  nomination controller.
- Nomination creation and custody belong to the Codex producer and are consumed
  by the route-nomination command.
- Consumption of the route evidence belongs to the named submitter. Its
  `routeUse` record names `consume-route-nomination` and the owner-admission
  sender. This permission covers use of the route, not permission to send a message.

Each record names its original issuer, actor, act, chat, acquisition `operationId`,
validity and revocation evidence, and consuming control. One original instruction
may cover all three acts. These records preserve evidence; they create no
permission. The caller checks current validity and applicable holds before each
act. At each send, independently bind the message's actual permission, holds,
correlation and attempt. An instruction limited to message A does not authorize
message B. Ordinary quota is the only supported credit profile.

The producer runs inside the exact receiving Codex chat. Use an actual supported
control to activate that chat when needed. This helper does not activate a chat
from another harness. If activation is unavailable, report that precise first-use
gap and the required receiver action; do not ask the operator to assemble
transport inputs or create a new relay case for each message.

The request's expected invocation contains the native control kind, exact chat,
task, attempt, command, working directory, and reviewed helper path and digest.
It contains no native item ID, completion status, exit code, or verified flag:
those facts do not exist until the command finishes. The actual Codex caller
must later corroborate the resulting native `commandExecution` item through its
trusted read control. A JSON field, argv value, process name, or old transcript
cannot establish the originating chat.

Supply current source-backed launch and listener references plus exact executable
identities for the helper, its direct app-server parent, and the Desktop main
parent. The supported discriminators are `invoked-helper`,
`direct-parent-app-server`, and `direct-parent-desktop-main`. If the installed
launch chain, main-process role, direct-primary listener rule, or executable
identity is unavailable, stop with that missing input. Do not substitute a PID,
endpoint, process-name scan, success flag, or retained build assumption.

## Collect And Publish

Choose one unused final path directly under an existing owned, nonsymlink,
mode-0700 publication root. Set the capture `run_root` to that directory, then
invoke the exact command recorded in the request:

```sh
python -B "$SKILL_DIR/scripts/codex_route_nomination.py" --request "$nomination_request"
```

The decoded request root must be an object with the supported schema. A list,
`null`, string, number, or malformed dictionary returns the ordinary
`invalid-nomination-request` result with `published: false` and
`no-connection-opened` closure before production observation or publication.

The production adapter starts at its own PID and walks the exact three-process
ancestry. It reads bounded process status, start ticks, parent edges, executable
identity, network namespace, boot ID, Desktop descriptors, the Desktop Unix
socket table, and route filesystem metadata. It classifies every listening Unix
stream held by the Desktop process, then accepts exactly one whose canonical
absolute path ends in `ipc/ipc.sock`, with an owned nonsymlink mode-0700 IPC
directory and mode-0600 socket. Unrelated listeners remain part of the bounded
sample but do not create direct-primary ambiguity. Alternate launchers,
shortened or legacy routes, multiple direct-primary listeners, incomplete
enumeration, unsupported roles, changed identities, or exceeded bounds refuse.

One five-second watchdog covers the whole sample: at most 16 admitted ancestors,
1,024 descriptor entries, 4,096 Unix-table rows, 512 KiB of Unix-table data, 256
KiB of descriptor-link data, and 8 KiB per metadata read. Each of exactly two
complete listener classifications retains those limits under the same watchdog;
their finite aggregate work cannot exceed 2,048 descriptor entries, 8,192 Unix
rows, 1 MiB of Unix-table data, or 512 KiB of descriptor-link data. The record's
existing four counters report the per-classification high-water values. Before
publication, the adapter rechecks every ancestor's parent edge, start ticks,
executable, role discriminator, and namespace, plus boot and filesystem identity.
It then performs the final complete descriptor and Unix-table classification.
The final set must contain the same sole canonical
listener with the same descriptor, socket inode, eligible flags, type, state,
and path. A final-only second canonical listener, lost listening eligibility,
incomplete pass, or exhausted per-classification or aggregate bound refuses;
unrelated native-pipe changes do not hide the unchanged sole primary.
Five seconds bounds acquisition only. This is one useful bounded final
observation, not an atomic snapshot or a
guarantee against later change. It is not a nomination, relay, grant, or attempt
expiry.

The command builds at most 4 KiB, stages and verifies the complete bytes through
`CaptureWriter`, and atomically publishes one mode-0600 record without replacing
an existing final name. Stdout contains only status, safe locator, size, SHA-256,
and `no-connection-opened` closure. An interrupted staging write remains
unadvertised. Retire only an exact abandoned staging entry attributed to the
original invocation; never scan or clean the directory broadly.

The record is a provisional path candidate. It does not establish
filesystem-to-kernel listener equivalence, provider or account identity, or
permission. Private means Unix-account-private: the named producer and authorized
sender may read the record for their bound acts, and safe status, locator, size,
digest, and closure may reach the authorized invoking chat or coordinator. Raw
endpoints, credentials, and unrelated captures remain protected. The path is a
locator, not authority. Modes 0700/0600 do not isolate hostile same-UID processes
or authorize every same-UID process.

## Corroborate And Consume

The default native PID namespace can expose only the helper and namespace PID 1.
Use the supported command-specific exception with direct `exec` when the selected
helper must observe the app-server and Desktop chain. This exception changes the
visible ancestry for that command. It does not select the target Concierge,
establish an account, or acquire an endpoint by itself.

After the command returns, use the caller's trusted native read to obtain the
actual `commandExecution` item and preserve the raw item or reference, chat and
turn, working directory, status, and exit. Its `command` field is an untruncated
shell-command string, not an argument vector. The native item does not expose an
attempt ID, helper digest, parsed arguments, or sandbox-profile field.

The trusted caller compares that raw command string with the exact shell command
it originally issued and corroborates the intended reviewed helper and arguments
against that original invocation. It also matches the raw working directory,
native item ID, chat and turn from the trusted read, completed status, and zero
exit. A mismatch stops before construction of the consumer input. Preserve the
raw evidence behind its `evidenceRef`.

Only after that corroboration, construct the existing owner-admission invocation
projection. Its `taskRef`, `attemptId`, exact chat, argument-list `command`, and
helper path/digest are caller-owned bindings to the original invocation and
reviewed bytes; they are not fields extracted from the native item. Add the raw
item ID, evidence reference, status, and exit to that projection, then give the
owner-admission procedure the safe nomination locator, exact size, and digest.
The projection does not turn its JSON fields into proof. The nomination command
cannot corroborate its own future completion.

The sender checks the unchanged record and its original acquisition invocation,
route-use permission, current message bindings, route and actual accepting process. App
restart, boot or namespace change, process or route replacement, different chat
or submitter, revoked permission, or an applicable hold refuses. A different
message or correlation alone does not require another nomination. Preserve the
original acquisition operation and native evidence when reusing the record;
create a separate immutable message and attempt for each independent send.
Elapsed time alone does not replace current checks or create a new attempt.

Synthetic fixture checks establish collection logic, bounds, selection,
complete-file publication, actor and grant binding, and guarded consumption.
They establish no current launcher or client compatibility, live process or
socket identity, provider or account identity, effective model, installation,
authority at an actuator, successful submission, or reply observation.
