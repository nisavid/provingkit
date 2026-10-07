# Observe the hook-selected executable as data

The collector's optional `executorObservation` samples its ancestry toward a
hook-supplied PID and hashes that ancestor's opened executable. It supplies a
bounded source prototype for [the accepted executable increment](https://github.com/nisavid/provingkit/issues/474).
The [collector contract](collector-contract.md) still governs input, output,
claims, and one-shot publication. Every record remains `unqualified`.

## Input and admission

The optional object has exactly these fields:

| Field | Meaning and limit |
| --- | --- |
| `processRoot` | Trusted absolute process-record root; `/proc` for a later approved Linux check, a disposable root for synthetic tests |
| `maxExecutableBytes` | Positive integer at most 268,435,456 (256 MiB), plus one overflow byte |
| `timeoutMs` | Integer from 10 to 30,000; separate observation wait limit, initially 30 seconds |
| `expectedSha256` | 64 lowercase hexadecimal characters naming independently assessed executable bytes |
| `executorKind` | `native` for this prototype; `interpreter` returns a named unsupported-input gap |

Absence of the object performs no process/image acquisition. Observation requires
a complete admitted Stop, matching whole setup text, a valid receipt window,
an ordinary fixture session, an exact `CLAUDE_CODE_SESSION_ID` match, and a
positive decimal `CLAUDE_PID` different from the collector. Initial collection
can remain unbound. Invalid admission emits `not_admitted` without starting the
reader. These checks compare asserted inputs; they do not authenticate the
producer or establish the Desktop task.

## Acquisition and evidence

The owned reader begins with the collector PID and follows parent IDs toward
the claimed PID. It acquires at most six selected `stat` records before the
executable read and rereads only those records afterward. Each read acquires
at most 8 KiB plus one overflow byte. Parsing handles closing parentheses inside
the command field. Retained output contains PID, parent PID, raw start-time
ticks, byte count, and local read interval, excluding the command name and whole
record. Cycles, a longer chain, malformed/oversized records, unavailable
processes, and changed parent/start-time samples leave incomplete evidence.
The root must use the same PID namespace as the claimed hook PID; later
integration must establish that assumption.

After reaching the claimed ancestor, the reader stats and opens only that
process's `exe` path as data. It hashes the opened regular ELF file up to the
configured ceiling and one overflow byte, requiring EOF for a digest. It
compares the opened file's device, inode, size, modification time, and change
time with its before/after stats and the path's target stats. It acquires no
textual symlink pathname, executes no file, reads no `environ` or `cmdline`,
walks no siblings, and inspects no registry. Changed or unavailable images are
incomplete. Overflow retains byte count without a digest. Successful output
retains both process samples, file identity samples, digest, and interval.
Equal samples do not prove uninterrupted identity.

`observed` means the bounded ancestry and opened-image checks completed. A
matching supplied digest yields `matches_configured_identity`; a different
digest yields `unassessed`, requiring graduated compatibility assessment.
Neither is qualification. An ELF header cannot distinguish a native Code engine
from an interpreter such as Node. The configured native role and expected
bytes need independent source evidence. This command alone proves neither that
role nor the selected Desktop-to-Code association. The task-binding and
selected-executor gaps remain until preparation supplies that evidence.

## Deadline and cleanup

The collector starts one helper with its own Node executable, no shell, an empty
requested environment, and no stdin or stderr acquisition. The helper reads
the selected records/image and sends at most 16 KiB of result JSON. The separate
timer includes startup. On timeout or excessive output, the collector sends
`SIGKILL` only to that owned helper, waits at most another 100 ms for `close`,
then stops waiting. `worker.cleanup` distinguishes observed exit, unconfirmed
exit, and a spawn/signal error. A signal request does not prove termination.
An unconfirmed helper remains a cleanup obligation with its recorded PID. The
[Node child-process contract](https://r2.nodejs.org/docs/latest-v24.x/api/child_process.html#event-close)
defines `close` after process termination and stream closure. No receiver or
unrelated process is signaled.

Executable failure or timeout preserves Stop evidence and emits an `incomplete`
facet with a named reason. It causes no retry or larger acquisition. The
deadline bounds observation waiting plus the cleanup grace, not total command
execution, publication, or receiver-turn duration. This prototype uses trusted
task-owned paths and inputs. It makes no claim of hostile-path containment,
authenticated identity, or private-data protection. Final launch, access, and
lifecycle controls belong to the preparation review and separate live grant.

## Consume the method

Before proposing a live check, load this reviewed revision with the collector
and fixture procedure; bind source-compatible native bytes, exact hook inputs,
PID namespace, process/image paths and ceilings, timing, output retention, and
cleanup. Record admission, Stop acquisition, executable observation, independent
task association, compatibility, and restoration separately. If helper exit is
unconfirmed, verify its identity and quiescence under the reviewed procedure
before deleting run artifacts. A retained PID alone never authorizes a signal.

Use `capturing-agent-procedures` when consuming this method and return source
corrections with the observations that support them. [Probe preparation](https://github.com/nisavid/provingkit/issues/278)
consumes the accepted prototype and separately chosen directory method. This
source increment activates no hook, reads no Claude process or private receiver
file, adopts no app patch, and introduces no Task Witness dependency.
