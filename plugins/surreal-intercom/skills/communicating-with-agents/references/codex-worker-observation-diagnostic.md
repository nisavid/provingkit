# Observe One Codex Worker Diagnostically

Use `../scripts/codex_worker_observer.py` only for a separately permitted,
one-shot diagnostic observation of one nominated local Codex conversation. The
command reuses Surreal Intercom's framed transport, cooperative exact-target
owner discovery, follower snapshots, and owned unfollow/close path. It does not
use a mailbox, claim an attempt, submit input, choose recovery, or start a
persistent reader.

Source and synthetic checks establish only the public command behavior they
exercise. They do not authenticate the discovered owner, prove that the route
reaches the server responsible for the target, establish upstream freshness or
cross-connection cursor continuity, measure owner-side work, qualify installed
history behavior, or authorize a native read. An explicitly permitted
diagnostic candidate may retain those identity and freshness questions; the
experiment intended to investigate them cannot require completed operating
qualification as an input.

## Prepare The One-Shot Input

The command accepts one UTF-8 JSON file through `--input` and creates one result
through `--output`. The result path must not exist. The input has exactly:

- `schema`: `provingkit-codex-worker-observation-diagnostic-v1`.
- Nonempty `observationId` and an `actor` with nonempty `threadId` and `hostId`.
- A `route` with the nominated Unix `endpoint`, `host: "local"`, exact `target`,
  and nonempty `routeRef` and `permissionRef`. These references preserve the
  caller's route and grant records; they create no permission or authentication.
- `scope` equal to `{"diagnosticObservation":true,"send":false}`.
- An explicit `profile` selecting every finite diagnostic limit below.

The initial experiment profile is:

```json
{
  "inputBytes": 1048576,
  "routeBytes": 65536,
  "frameBytes": 65536,
  "incomingBytes": 262144,
  "events": 64,
  "resultBytes": 8192,
  "stdoutBytes": 8192,
  "stderrBytes": 8192,
  "outgoingFrameBytes": 4096,
  "writes": 70,
  "networkSeconds": 10,
  "ioSeconds": 1,
  "cleanupReserveSeconds": 1,
  "observationSeconds": 1,
  "maxReceiptAgeSeconds": 10
}
```

These values are selected experiment inputs, not measured demand or production
policy. A caller may tighten numeric ceilings within the command's supported
maxima; the cleanup reserve remains one second. The command never expands a
refused limit or retries with another profile.
`inputBytes` covers the complete input, including the route record;
`routeBytes` additionally bounds that record. `incomingBytes` counts frame
headers and bodies across initialization, discovery, unsolicited messages,
observation, and cleanup on the owned connection. `events` is likewise shared.
The outgoing frame and write limits cover initialize, exact-target discovery,
follow, unfollow, and generated `canHandle: false` discovery responses. No
turn, message, model, settings, recovery, or mailbox operation is permitted.

Run the contained source command without changing sibling import resolution:

```sh
python -B plugins/surreal-intercom/skills/communicating-with-agents/scripts/codex_worker_observer.py \
  --input diagnostic-observation.json --output diagnostic-result.json
```

The command returns zero only after a bounded snapshot result is finalized. It
returns two for a retained refusal or unknown observation, and three when the
create-only output collides or cannot be finalized. Stdout carries only a small
terminal summary; stderr is empty for handled outcomes. The result file, not a
zero exit alone, is the consumer observation. Finalization removes only the
staging file this invocation created; a preexisting file, symlink, or directory
at the staging path is preserved and produces the bounded exit-three refusal.
Failure to remove an invocation-owned staging file also produces that bounded
refusal, without replacing an earlier finalization failure. Output-path probes
repeated after observation belong to the same finalization boundary: an
inaccessible path produces the bounded finalization refusal, while a successful
positive probe remains an output collision.

## Interpret The Result

The result reports the snapshot-reported activity (`active`, `idle`, or
`unknown`), local receipt time and age, first/last history support and
completeness, acquisition counters, selected-view comparison, terminal reason,
and owned subscription/connection closure. It retains no raw history.

The selected view contains only `threadRuntimeStatus.type`, `turns[].turnId`,
and `turns[].status`. Equality says only that those fields were equal in the
first and last supported snapshots acquired on this connection. Work can
change outside that view. Equality establishes neither unchanged work nor a
legitimate wait. A positive comparison does not authenticate the server or
prove upstream freshness, and snapshot revisions are not proved
cross-connection cursors. Unsupported text runtime states remain visible as
their raw values and cannot compare equal merely because both project to
unknown activity. Present non-text runtime-state types are malformed records,
not selected-view values. Byte-identical snapshots at one revision are harmless
duplicates;
different state at one revision makes the observation unknown.

Follower snapshots can carry whole history before the command projects the
selected activity fields. The command therefore does not establish a
metadata-only or cheap quiet-polling route. Partial history stays incomplete;
unsupported history stays unsupported. Reset, stale, mismatched, malformed,
partial, over-limit, or missing evidence remains refused or unknown rather
than being converted into inactivity. The embedded conversation ID must match
the nominated target as well as the outer stream binding. Every completed
record returned by initialization, owner discovery, following, and unfollow is
processed once in wire order, including records completed before a terminal
frame failure. A malformed record does not suppress later completed evidence.
Owner-discovery status is reconciled against the owner named by the correlated
response before follow; an unrelated client's disconnect does not invalidate
that binding. Before a nonblank owner is known, unrelated or unidentified
dictionary status records remain non-evidence, while state records are refused.
Every accepted state record must name that known owner as its source. A reset
or owner disconnect during discovery or cleanup, and a
terminal framing, event, or aggregate-wire failure after a valid snapshot,
therefore remains visible and invalidates success without erasing the acquired
snapshot or counters. A cleanup record failure remains separately visible as
`closure.cleanupFailure`; reset and owner-disconnect invalidations take
precedence as the terminal reason. Clean EOF before another frame remains
closure uncertainty. State broadcasts require an array of nonempty
target-client IDs. State changes require a nonempty text type, snapshot changes
require an object conversation state, snapshot revisions require a non-Boolean
integer, present runtime-state types require text, and each projected turn ID
must be a nonempty string. A snapshot is projected and validated before its
revision, conflict, or selected-view bookkeeping is committed. Malformed state
changes remain bounded refusals so later completed records are still processed.
Unsupported turn IDs make history and selected-view equality unknown rather
than producing a false comparison.

The ten-second network budget includes connection work, follow acquisition,
unfollow, and its reply wait. Each connect/read/write receives no more than the
selected one-second per-I/O allowance or remaining phase budget, and the final
second is reserved for cleanup once following begins. The result distinguishes
unfollow uncertainty from owned stream closure. Python's local socket close and
the foreground process itself are not a host process-supervision guarantee.

## Qualify A Later Native Comparison Separately

A later native experiment needs a reviewed candidate revision, one concrete
route and target, and a fresh grant covering that acquisition. Retain its
actual input, command, exit, result, wire/client/elapsed counters, independent
native selected view, and closure. Compare only the named fields and preserve
all identity, freshness, history, cost, and owner-side unknowns. Refusal does
not permit expansion, retry, route substitution, scheduling, or recovery send.

A recurring caller, process-service supervision, roster/due bookkeeping,
reservation, conditional continuation, pilot admission, disable control,
installation, and recovery activation remain separate work under the maintained
Worker-recovery contract.
