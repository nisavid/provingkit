# Reader and hook evidence experiments

These experiments show how explicitly supplied receiver records and Stop-hook
events can yield useful candidates while retaining missing evidence. They are
source prototypes for [the reader/hook increment](https://github.com/nisavid/provingkit/issues/393),
outside installed Rolecasting. Every result remains `unqualified`; no result
authorizes a send, retry, or private read.

## Interfaces under test

The operator agreed these interfaces in
[the component decision](https://github.com/nisavid/provingkit/issues/388#issuecomment-5961209463):

- `inspectRecords(input)`: supplied metadata and JSONL text, expected task/Code
  identities, an example notice/ACK rule, observation times, and a compatibility
  assessment produce record candidates and gaps. It performs no I/O.
- `readSelectedFiles(input)`: explicit metadata and transcript paths plus the
  same interpretation inputs produce evidence and an acquisition description.
  It opens only those paths, without discovery or SDK directory lookup.
- `projectStop(input)`: a supplied hook event, expected Code identity, example
  ACK rule, capture times, and collector coverage produce bounded evidence.
  It neither installs a hook nor reads the event's transcript path.

Tests use invented data at these public interfaces. The filesystem examples
use disposable regular files. This is not a containment mechanism for hostile
paths or a qualified live acquisition tool. Tests of record binding establish
parser behavior, not authenticity of the producer or authority to read it.

## Evidence model

The example notification and ACK texts must match whole text bodies. A quoted
line, substring, user echo, or wrong peer is insufficient. This is a specimen
grammar for the experiment; the eventual notify interface owns the real grammar.
The sample peer origin uses `kind` and `senderTaskId`; actual external native
ingress remains unobserved. Original record IDs, timestamps, and the selected
origin fields accompany candidates without becoming authenticated provenance.

Record timestamps and capture intervals are caller-supplied observations. A
recent file read cannot freshen an old matching message. Missing, malformed,
partial, stale, conflicting, or differently bound inputs remain explicit gaps.
No record is not proof of refusal or non-delivery. Stable file metadata does
not establish flush completeness, a coherent snapshot, or uninterrupted history.

Compatibility is separate from evidence completeness. The caller may supply an
assessment and reference; default `unassessed` does not mean incompatible.
Demonstrated incompatibility disables this prototype's affected interpretation.
An assessment reference is not independently verified by the prototype.

Stop's optional last assistant message supplies an ACK candidate only. It does
not establish incoming delivery, Desktop/native-peer binding, or full runtime
state. Event-time cwd and permission mode, when present, are partial fields.
Collector gaps remain visible and do not become continuity claims.

## Completion and limits

Use `tdd` at the agreed interfaces; retain meaningful red/green observations.
Freeze the first prototype findings before exchanging them with the identity
and runtime-producer research tracks. Reconcile contradictions while tracks
remain open, then review and publish one final candidate. The later experiment
decision owns the operator's reaction and adoption choices.

Full actual-state snapshots belong to initial qualification and affected
requalification. These prototypes provide none. Ordinary sends retain fresh
peer/consent checks, receiver-origin delivery, and explicit correlated ACK.
No Desktop access, private receiver read, hook activation, task creation,
restart, model prompt, or notification is part of this experiment.
