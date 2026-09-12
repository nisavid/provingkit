# ADR 0001: Store response outcomes as immutable record files

## Status

Accepted for the first Provingkit feedback-response implementation.

## Decision

Store each Response Outcome Bundle as one version-2 format marker, an ordered
`records/` directory, a `staging/` directory, and one local exclusive lock. Each
committed record is canonical JSON containing its schema version, monotonic
sequence, kind and ID, prior record digest, payload, and payload digest. Its
filename contains the sequence and record digest.

`SemanticHistoryFold` owns one private `ResponseIdentityAuthority`. The module
constructs exact provider-observable correlation values, derives current
effective-unknown groups, and applies every typed-identity observation,
reservation, transfer, conversion, and claim inside the fold's per-record
transaction. The fold commits semantic and identity projections together only
after the complete record passes. Runtime consumes the resulting closed
reconciliation decision and does not interpret raw attempt or identity maps.

Possible-result equivalence includes the stable typed repository and PR target,
PR number, exact operation and response object kind, full placement, actor, and
complete opaque body wrapper. It excludes head/base OIDs, repository names and
owner, head repository, and permalinks only because a response object cannot
attribute those values. Those fields remain required for every admission,
replacement, carry-forward, and prewrite comparison. Canonical object equality
is authoritative; SHA-256 is only an index.

An identity has one lifetime intent across observation, reservation, and
ownership. More than one current effective unknown in one correlation group
prevents collection attribution for every member without freezing a separately
validated group. Reservations commit before reread and survive restart;
`still_unknown` converts them to same-intent observation, and exact success
converts them to ownership. Any cross-intent role relation or partial transition
invalidates the whole history before provider access.

Use only the closed semantic record set: atomic ordinary/follow-up admission,
carry-forward, validation start, terminal invalidation, write start, atomic
attempt resolution, reconciliation start/resolution, runtime-produced
replacement basis, and atomic basis-consuming replacement.
Before any provider-capable action, fold every record and validate its exact
payload variant, full retained acquisition/source/binding evidence, state
ordering, cardinality, all references, and exclusive response identities. An
unknown or unsupported record is not irrelevant; it invalidates the bundle and
causes zero provider calls.

Publish a record under the lock by creating a unique mode-0600 staging file on
the same filesystem, writing the complete bytes, changing it to read-only,
syncing it, closing it, hard-linking it to a no-replace final name, and syncing
the records directory. Never edit, rename, remove, or replace a committed
record. Ignore and report staging remnants. Sequence gaps are valid; digest,
schema, ownership, reference, or identity-claim failures block the bundle.

Before lock creation, reject any state directory containing
`bindings.jsonl`, `attempts.jsonl`, `leaf_receipts.jsonl`, or `outcomes.jsonl`
with `unsupported-development-format`. Preserve every legacy byte. The runtime
has no importer, converter, dual writer, truncation, or repair flow.

## Why

A live JSONL tail can be partly written. Retaining that tail preserves bytes but
makes the next restart unable to distinguish a committed record from a torn
record; truncating it would destroy evidence. A mutable database would add a
general ledger and recovery framework beyond the two operation-specific
actuators.

Immutable no-replace files make the committed prefix inspectable after every
observable fault. A failure before the final link leaves only a staging remnant.
A failure syncing the directory after the link may leave a valid committed
record, which restart accepts conservatively. In particular, a surviving
`write_started` keeps effect and immediate drift `unknown` and forbids another
provider write.

## Supported boundary

This decision assumes reliable local POSIX `flock`, same-filesystem atomic hard
links, regular-file `fsync`, and directory `fsync` in one trusted same-user,
same-machine state directory. NFS, object-backed mounts, cloud-synchronized
directories, and filesystems that do not honor those primitives are unsupported.
The runtime does not detect the physical backing store, certify durability, or
coordinate separate directories or machines.

The digest chain detects accidental inconsistency. It does not authenticate
records against the trusted local user. Provider-side exactly-once execution,
an atomic transport batch, host provisioning, and cross-machine exclusion remain
outside this boundary.

## Consequences

Every provider-capable invocation exercises lock, staging write, file sync,
no-replace link, and directory sync before the provider call by committing
`write_started`. An observed primitive failure before that commit returns a
storage-capability diagnostic and makes no provider call. A storage failure
after the call follows missing-leaf or semantic-persistence reconciliation and
cannot be reported as a pre-call capability failure.

The bundle can retain one source-revision owner, immutable intent and attempt
links, exclusive full typed response identities, and sticky post-write drift.
Historical `unknown` drift cannot become `not_observed` from a later matching
acquisition.

Commit `prewrite_validation_started` before its provider reads. Observed drift
commits terminal invalidation; an interrupted validation remains terminal for
the old intent. Replacement is two-phase. `prepare-replacement` first validates
the whole bundle, acquires a complete successor epoch after the terminal record,
and atomically records a read-only basis bound to the terminal record digest,
one exact source, its scope, and its route. Four exact canonical authored
artifacts then bind classification, adjudication, authority, and writer result
to that basis. One atomic replacement consumes the latest unsuperseded basis
and creates the linked successor. Caller timestamps, freshness labels, and
predecessor artifacts supply no replacement authority. Attempt and
reconciliation resolutions atomically contain their outcome, provider evidence,
drift, and identity observations or claim, so restart never joins a partial
success.

Reconciliation resolution has two results: `confirmed_success` for one stable,
exclusive response whose typed identity, actor, operation, and exact bytes are
verified, and `still_unknown` for empty, ambiguous, or incomplete observation.
The fold derives one effective disposition and outcome for the current attempt;
a reconciliation success completes replay without rewriting its original
unknown outcome. Before a selected reconciliation candidate is reread, a
committed round reserves its full typed identity. Supersession transfers the
same reservation or converts a different one to permanent same-intent
observation; resolution converts it to ownership or observation.
Its retained `absence_evidence` field is always null. Unknown never becomes
retry eligible and cannot be replaced, carried forward, rebound to a fresh key
or body, or retried through an authored no-write assertion. Same-key retry
remains available only after an already conclusive, retryable
`confirmed_failure` whose operation-produced receipt proves a `none` side
effect, followed by full unchanged-binding revalidation.

Envelope version 2 does not grandfather unsafe semantic history. An old
replacement transition without a preceding eligible basis and four exact
basis-bound artifacts, a reconciliation naming an earlier attempt, or a
conflicting reservation invalidates the complete bundle before provider access.
The runtime preserves the committed bytes and performs no migration, repair, or
retroactive basis append.
