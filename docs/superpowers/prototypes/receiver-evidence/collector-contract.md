# Collect one fixture Stop event

`collector.mjs` turns one inherited stdin pipe into a bounded observation file
for the proposed disposable-fixture check. It wraps the reviewed Stop projector,
adds acquisition and file lifecycle behavior, and keeps the first task identity
unbound until an independent witness can be checked. It is source equipment for
[collector preparation](https://github.com/nisavid/provingkit/issues/407), outside
installed Rolecasting. Every record remains `unqualified`.

The [accepted experiment decision](https://github.com/nisavid/provingkit/issues/397#issuecomment-5972295427)
authorizes synthetic implementation at the command interface. The
[fixture procedure](fixture-check-procedure.md) is a proposal for later review
and authorization; neither artifact activates a hook.

## Command interface

```sh
node docs/superpowers/prototypes/receiver-evidence/collector.mjs --config work/config.json --output work/result.json
```

The caller supplies a regular UTF-8 JSON configuration file and an inherited
pipe containing one serialized hook event, then closes that pipe. The output's
parent directory must already exist. This prototype supports Linux pipe input
and a trusted, task-owned local directory. A terminal or redirected regular
file is not its stdin interface. Paths and parent directories are trusted
inputs; this is not hostile-path containment, producer authentication, or a
qualified private-data protection mechanism.

Configuration has these required fields and one optional observation object:

| Field | Meaning and limit |
| --- | --- |
| `schema` | `1` |
| `runId` | Nonempty string, at most 256 UTF-16 code units; identifies this proposed check |
| `expectedCodeId` | `null` for initial acquisition, or a separately supplied nonempty Code identity of at most 256 code units |
| `expectedFinalText` | Exact whole setup-response text, at most 4,096 code units |
| `since` | Nonnegative epoch milliseconds for the beginning of the accepted capture window |
| `maxInputBytes` | Integer from 1 to 1,048,576; interpretation ceiling for serialized stdin |
| `inputTimeoutMs` | Integer from 10 to 60,000; elapsed stdin acquisition limit |
| `executorObservation` | Optional object in the [executable contract](executor-contract.md); absence performs no process/image acquisition |

The command reads at most 32 KiB plus one overflow byte from the configuration.
Stdin acquisition reads at most `maxInputBytes + 1` bytes. It neither opens the
event's transcript path nor discovers metadata. The complete acquired event
can nevertheless contain transcript paths, cwd, permission mode, assistant text,
background commands, and cron prompts. Smaller retained output does not narrow
that acquisition.

The application selects `CLAUDE_CODE_MESSAGING_SOCKET`, retained up to 4,096 code
units. Optional executable observation also selects `CLAUDE_PID` and
`CLAUDE_CODE_SESSION_ID` under its admission checks. A missing or
larger endpoint becomes a gap. This is an asserted endpoint observation; the
command does not connect to it, encode a sender destination, authenticate the
peer, or grant consent. A real Node launch also inherits environment before
JavaScript starts: a reviewed live launcher must enumerate that environment
and account for runtime-affecting values such as `NODE_OPTIONS`. The prototype's
field selection is not an environment isolation claim.

## Observation meaning

The record includes its run ID, `fixture_stop_check` purpose, acquisition status,
observed byte count, EOF result, wall-clock receipt interval, binding state,
projection gaps, and the selected endpoint where applicable. It has no raw
event copy. Capture time is local receipt time, not text production time or a
freshness proof at a later inspection.

With a configured Code ID, the command retains the projector's partial fields
and puts a matching setup response in `responseCandidate`. A different Code ID
or event becomes a mismatch without a receiver endpoint. The configured ID is
an input, not independently established identity. A response candidate is not
a notification acknowledgment.

With `expectedCodeId: null`, a complete Stop event with a valid observed Code ID,
matching setup text, and ordered receipt window may supply `unbound.observedHookSessionId`
and `unbound.matchingFinalText`. Optional `unbound.eventFields` retain cwd
(up to 4,096 code units) and permission mode (up to 128), with missing or
oversized fields named in `unbound.gaps`. They describe the unbound event;
cwd may contain the producer's fallback and mode is a partial permission fact.
The known `served:` session kind is excluded from this ordinary Desktop
fixture in both modes. Other strings remain unclassified hook session identities
until the independent join; a length check does not establish a Code identity.
The projection remains unknown and
`responseCandidate` remains null. The observed ID is never fed back as its own
expected ID. The subsequent UI/metadata join belongs to the reviewed procedure;
replaying this file through the command would create new receipt timestamps and
is not reconciliation.

For unbound input, the receipt window requires `startedAt >= since` and
`completedAt >= startedAt`. The configured-ID projector also rejects capture
age greater than `inputTimeoutMs`. The pipe timer bounds acquisition in both
modes; neither receipt rule establishes producer freshness or a total command
deadline. The output reports acquired bytes and EOF only; unread or future
producer bytes are unmeasured.

Malformed UTF-8/JSON, wrong event shape, missing text, mismatches, byte overflow,
timeout, and read failure cannot qualify the route. Absence of an observation
does not establish refusal or nondelivery. No outcome causes a resend.

The optional [hook-selected executable observation](executor-contract.md) adds
a separate facet after admitted Stop acquisition. Its incomplete result preserves
the Stop evidence. Observed image bytes do not establish the selected Desktop
task, native Code role, compatibility, or qualification. The independent binding
and selected-executor gaps remain until the preparation join resolves them.

## Files and termination

For a configured output `result.json`, the public lifecycle is:

1. Validate configuration, then exclusively create `result.json.claim` before
   reading stdin. Its run ID and collector PID describe ownership only. The PID
   does not identify the receiver engine and is not a process-authentication
   witness. An existing claim prevents another event acquisition.
2. Acquire one bounded event or record an acquisition gap. Publish at most
   64 KiB of JSON through `result.json.partial`: create exclusively, write,
   synchronize the file, close it, and link the completed bytes to `result.json`
   without replacing an existing destination.
3. Remove the temporary file after success or a handled publication failure.
   Keep the claim through both outcomes. Reuse requires a separately reviewed
   new run slot; deleting the claim to retry is not automatic recovery.

Exit `0` means the command completed publication and its normal cleanup. The
record may still be unknown. A caught command/configuration/publication failure
returns `1` with a constant diagnostic and no event data on stdout or stderr.
The command never deliberately returns the blocking-hook code `2`. Actual
receiver treatment of failure and early stdin closure remains a live check.

An abrupt signal can leave a claim and partial file. Neither is a completed
observation. A signal after linking can leave a complete result even when the
caller loses the exit result; inspect existing files under the grant before
any new action. File synchronization and linking do not claim survival of a
host crash or directory-metadata durability. Filesystem operations themselves
have no total execution deadline. Stdin acquisition and the optional executable
observation have distinct wait limits; neither bounds publication.

The supervising procedure owns removal of the exact recorded run artifacts
after collection is quiescent and required evidence is retained. It preserves
other files and concurrent settings changes. No broad directory deletion or
unrelated process termination is part of the command.

## Synthetic evidence and dependencies

```sh
node --test docs/superpowers/prototypes/receiver-evidence/reader.test.mjs docs/superpowers/prototypes/receiver-evidence/hook.test.mjs docs/superpowers/prototypes/receiver-evidence/collector.test.mjs docs/superpowers/prototypes/receiver-evidence/executor-command.test.mjs
```

The command tests use invented events, a selected synthetic environment, and
temporary directories. Linux `prlimit` imposes a write-size limit on one child
to exercise an interrupted output write; it changes no parent or Desktop limit.
The tests cover valid and unbound input, wrong identities, missing fields,
oversized/malformed/stalled input, invalid configuration, consumed run slots,
interrupted publication, occupied destinations, and termination cleanup states.
Node.js 24.21.0 ran the initial 34 combined checks successfully. Cross-examination
added optional-field and served-session command checks; the revised suite has
36 checks. The executable extension adds 14 command checks; all 50 pass on
Node.js 24.21.0. They cover admission, ancestry limits/cycles, bounded malformed
records, overflow, replaced/vanished processes, timeout and owned-helper exit,
interpreter/non-ELF gaps, changed-build classification, endpoint samples, unbound
collection, and configuration ceilings. One controlled test-owned Linux child
exercises actual `/proc` and opened-image mechanics. It is a Node image, not a
Claude executor or evidence of a native Code role. No Claude process or private
receiver file is involved.

The bounded pipe reader uses the documented
[`net.Socket` `onread` buffer interface](https://nodejs.org/api/net.html#new-netsocketoptions)
around fd 0; it creates no connection. A stalled `fs.read` experiment wrote the
timeout record but kept the process alive until EOF. The retained regression
checks process exit as well as output, and the interruptible pipe implementation
passes it. No hook was installed and no native receiver was observed.

Source and synthetic evidence establish this command's stated behavior, not
actual hook loading, executor identity, task binding, complete event capture,
private-data protection, or receiver effects. Those claims need the integration
and appropriate security review in the preparation join, followed by the
separate live grant and observations. A new dependency version is unassessed;
use graduated compatibility checks on affected behavior.
