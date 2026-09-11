# Feedback Response Contract

One response intent binds one exact source revision to one operation and at most
one resulting GitHub object. The semantic owner decides what an authorized
response says and where it belongs; the selected Provingkit actuator alone
records the provider request, result, stable identity, and exact reread.

## Sources and placement

| Typed source | Response operation | Required placement evidence |
| --- | --- | --- |
| Inline review comment, including an intermediate reply | Reply in its existing review thread | Exact source comment, containing thread, and root comment identities; current placement and thread state |
| PR conversation comment | Create one PR conversation comment | Verified PR target and natural visible permalink to the exact source |
| Nonempty submitted-review body | Create one PR conversation comment | Verified PR target and natural visible permalink to the exact review |

A review body and its inline comments are separate sources. Several findings
inside one source can share a response; findings from different objects do not
share a response object. Adjudicate a duplicate summary independently rather
than suppressing a whole review or automatically replying to it.

Retain repository-qualified PR identity, explicit source kind, typed provider
identity, permalink, full observed body identity, author and timestamp evidence,
GitHub state, placement, and the associated revision when GitHub exposes it.
Record genuinely unavailable optional evidence explicitly. Missing required or
contradictory evidence blocks admission. URLs locate objects; they do not supply
typed identity. The complete epoch carries one identity-registry digest over
pull requests, reviews, conversation comments, inline comments, review threads,
and association stubs. Exact repeated observations deduplicate; remapped or
changed repeats fail the whole epoch. Review threads carry their node ID and an
explicit unavailable database-ID component because the public schema does not
expose one. Empty or pending review bodies remain metadata.

The qualified repository includes its public Repository node ID and database
ID. The epoch also retains the actual local acquisition start and end
observations and the complete page trace for every top-level collection and
hydrated thread. Local acquisition observations are not provider timestamps.
Required absent, contradictory, or incomplete evidence fails the epoch; do not
supply a compatibility default or infer a missing provider value.

Replying to a resolved or outdated inline source keeps it in that thread and
preserves the observed state. The provider's root-comment reply address does
not replace correlation to an intermediate source comment. A conversation
response uses GitHub's shared IssueComment endpoint only after verifying a PR
target. Neither operation can create a review or mutate an Issue's lifecycle.

## One source-revision owner

Resolve the qualified PR and exact typed source revision to one permanent
ordinary owner before considering the caller's key. The caller supplies a
durable intent key, source revision, PR/head, operation,
placement, classification, adjudication and authority evidence, writer
identity, and exact body
identity. Select applicable writing policies and include the top-level source
link before the portable writer fixes the body. Keep those bytes opaque through
the actuator, including CRLF and terminal-newline state. No marker injection,
body edit, or automatic formatting occurs during dispatch or reconciliation.

The owner identity uses the Repository's typed database/node identity, the pull
request's typed database/node identity and number, the source kind and typed
database/node identity, and the exact source revision object. Runtime admission,
semantic folding, and replacement-basis validation use one canonical private
constructor and compare its typed values; digests only index them. Repository
name and owner, PR permalink, head/base, head repository, source permalink,
thread state, placement, and relevant-comment set remain complete epoch and
prewrite evidence. Changing those fields cannot create a second owner, and it
cannot make a stale binding writable.

An exact replay returns the existing result. Any changed binding conflicts
before a write. Identical bodies attached to different sources remain distinct.
Ordinary source-revision ownership prevents a fresh key from producing a second
response. A separately authorized correction or addendum uses a new
intent linked to a confirmed predecessor outcome; it never replaces the prior
response and cannot resolve an unknown attempt by assertion.

An unexecuted intent invalidated by source, head, or relevant-context drift, or
left after an interrupted validation, is terminal. Replacement is two-phase.
First, `prepare-replacement` validates the entire bundle, acquires a complete
epoch after the terminal record, and durably records one exact successor source,
scope, route, terminal record digest, and optional prior-basis supersession. The
basis grants read evidence, not response authority. Second, the semantic owner
reclassifies, re-adjudicates, reauthorizes, and reruns the writer against that
exact basis. The atomic replacement consumes the latest unsuperseded basis once,
creates the linked successor intent, and creates a new owner only when the source
revision changed. A `write_started` permanently closes this route, including
after a confirmed provider failure. This transition is not a retry,
reconciliation, follow-up, or operator override.

If rename or transfer prevents the predecessor repository name from resolving
to the current Repository and pull request, replacement preparation stops before
classification, adjudication, authority, or writer authoring. The acquisition
owner must resolve a current locator to the same stable typed identities. A
freshly acquired epoch can then reuse the permanent owner while carrying its new
complete mutable context through basis consumption and prewrite validation.

## Acquisition epochs

Acquire complete paginated evidence and bind it to the PR head. This is an
observational epoch, not an atomic GitHub snapshot. Immediately before each
write, revalidate the exact source, placement/thread, relevant comment set,
head, authority, selected operation, and body binding. Source edits, deletion,
inaccessibility, thread changes, late feedback, and head drift end the epoch.

After publishing a source fix, reacquire against the new head before authoring.
A fresh epoch may carry forward only pending intents proven independent and
unchanged in source revision, head, authority, placement, and exact body.
Completed receipts remain credited. A correlated actuator-created response is
a result; a reviewer's reply is a new source. Every later run reacquires current
GitHub evidence instead of using the outcome bundle as a state oracle.

## Attempts and reconciliation

| Leaf result | Permitted next step |
| --- | --- |
| `confirmed_success` | Record and credit the exact verified response. |
| `confirmed_no_op` | Complete an exact replay with the existing result. |
| `confirmed_failure` | Retry only if evidence proves no write, the typed reason is retryable, and the same unchanged intent passes full revalidation. |
| `unknown` | Reconcile under the same key; never automatically write again. |

Reconciliation first rereads a retained complete response identity when one is
available. Otherwise it acquires the complete response collection and excludes
candidates observed, reserved, or owned by another intent. Before a selected
candidate is reread, a committed reconciliation round reserves its operation-
specific kind, positive database ID, and node ID for the current effective
unknown attempt. A successor round explicitly supersedes an incomplete round.
The same candidate transfers; a different candidate closes the old reservation
into permanent same-intent observation. Success converts the reservation to
exclusive ownership, while `still_unknown` converts it to permanent observation.
One stable, exclusive result
whose actor, operation kind, typed identity, and exact writer bytes all agree
confirms success. Empty, multiple, or incomplete observations remain unknown.
Every reconciliation resolution retains `absence_evidence: null`; an authored
no-write assertion grants no retry capability. A new key, changed body, or
operator assertion cannot bypass an unknown attempt. Preserve uncertainty when
the available provider evidence cannot distinguish no write from a delayed,
edited, or deleted result.

One private `ResponseIdentityAuthority`, owned by the semantic-history fold,
decides that order and owns every observation, reservation, transfer,
conversion, and ownership claim. Callers pass only the validated record kind
and payload; they never assemble competing-intent sets or proposed identity
maps. Each record is one private transaction. Semantic disposition and identity
projections commit together after all validation, or neither commits.

Its possible-result correlation value is exact canonical data: stable typed
repository identity, stable typed PR identity and number, operation, derived
response object kind, full placement, expected actor login, and the complete
body wrapper. `create_inline_reply` maps only to `PullRequestReviewComment`;
`create_pull_request_conversation_comment` maps only to `IssueComment`.
Repository names and owner, PR permalink, head and base OIDs, and head repository
remain mandatory admission, replacement, carry-forward, and prewrite evidence,
but they are absent from possible-result equivalence because the response object
does not prove them. SHA-256 may index the canonical value and never replaces
field-for-field equality.

Every current attempt that crossed `write_started` and whose fold-derived
effective disposition remains `unknown` belongs to its correlation group. This
includes an unresolved write-start prefix, an original unknown outcome, and
every later `still_unknown`; it excludes unexecuted and conclusive states. A
collection result is attributable only to the sole member. Two equal members
remain unknown without collection listing or any identity role, even across
different acquisition heads on the same stable typed PR. A different group may
continue after its own independence and complete-binding checks.

A full typed response identity has one lifetime intent across observation,
reservation, and ownership. Cross-intent owner-observer,
observer-reservation, reservation-claim, observer-observer,
reservation-observation, and owner-reservation relations invalidate the whole
history before provider access. Same-intent reservation transfer, conversion to
observation, and conversion to success ownership remain valid. A nonnull start
must commit before reread; a failed start publication forbids that reread, and a
surviving reservation remains exclusive after restart.

Persist every admitted intent, attempt, authoritative leaf receipt, and semantic
outcome in an append-only, versioned Response Outcome Bundle. Outcomes bind
source revision, adjudication and authority, PR/head, operation/placement,
intent, writer/body identity, and the immutable leaf receipt identity or digest.
Retries link only to the immediately preceding retryable `confirmed_failure`
whose operation-produced receipt proves `side_effect: none`. Reconciliation
links to the current effective unknown attempt, and follow-ups link to
predecessor outcomes. The fold retains every original resolution and derives one
effective disposition and outcome for each attempt. A reconciliation success
therefore completes exact replay and can authorize a separately admitted
follow-up without rewriting the original unknown result. Repeated identical
`still_unknown` rounds retain distinct outcome identities. Preserve earlier
evidence.

Ordinary owner/intent creation and follow-up admission are each one atomic
record. Commit `prewrite_validation_started` before any validation read. The
actuator may run only after `write_started` commits with effect and post-write
drift both `unknown`. A pre-write drift record closes that validation as
`invalidated_unexecuted`; an interrupted validation has no terminal record and
is `validation_indeterminate`. Both permanently close the old intent even if
the provider later reverts.

An attempt resolution atomically records the provider result, every identity
observation, the exclusive identity claim when present, exact byte and actor
evidence, drift, and semantic outcome. Success requires operation kind,
database ID, node ID, actor, and exact writer bytes to agree across create,
requested reread, and reread. Every complete observed response identity is
exclusive to one intent, including unknown evidence and reconciliation
reservations. Another intent's equal body, actor, thread, timestamp, or URL
cannot claim that object.

If GitHub confirms a write and semantic persistence fails, retain the leaf
receipt and forbid another write until reconciliation. If source or thread
state drifts after an exact response is uniquely verified, credit that write
against its preimage and report the drift for the next epoch. Neither case
supports an all-feedback-addressed claim.

Record immediate post-write drift as `observed`, `not_observed`, or `unknown`.
Observed evidence is sticky. A missing leaf or incomplete check falls back to
durable `unknown`; a later matching acquisition cannot reconstruct the interval
or change it to `not_observed`.

Several responses are independent one-intent invocations, each with its own
authority, revalidation, writer output, key, attempt, and receipt. Unknown
freezes dependent or conflicting work; proven-independent intents may continue
after revalidation. No batch atomicity, implicit rollback, or cross-machine
serialization is claimed by this local response path.

Reaction, thread resolution or reopening, review submission, PR publication or
merge, Issue operations, and historical repair require their separate owners.
These response actuators perform none of them. Local authority evidence and
development receipts do not establish production, release, or host authority.

## Runtime interface

Use `scripts/response_cli.py` relative to this skill directory. `acquire` performs
complete typed acquisition; `prepare-replacement` records a post-terminal basis
without posting; `invoke` handles one admitted intent; `reconcile` observes an
existing intent without posting; `outcomes` reads the bundle.

```sh
python scripts/response_cli.py acquire --repo OWNER/REPO --pr NUMBER
python scripts/response_cli.py prepare-replacement --state-dir STATE --intent-key KEY --repo OWNER/REPO
python scripts/response_cli.py invoke --state-dir STATE --intent INTENT.json --body-file BODY.md
python scripts/response_cli.py reconcile --state-dir STATE --intent-key KEY
python scripts/response_cli.py outcomes --state-dir STATE
```

Keep `STATE` durable across invocations. It contains a version-2 marker and an
ordered `records/` directory of immutable canonical-JSON files linked by digest.
Publication uses a mode-0600 same-filesystem staging file, complete write,
read-only mode, file sync, no-replace hard link, and records-directory sync under
the exclusive bundle lock. Report and ignore staging remnants; never edit,
rename, remove, or replace committed records.

Reliable local POSIX `flock`, same-filesystem atomic hard links, regular-file
`fsync`, and directory `fsync` are supported input assumptions. Keep the state
off NFS, object-backed, cloud-synchronized, and other filesystems that do not
honor them. Successful primitives do not certify physical durability or detect
the backing filesystem. Separate directories and machines do not coordinate.

Before lock creation or any provider call, the presence of `bindings.jsonl`,
`attempts.jsonl`, `leaf_receipts.jsonl`, or `outcomes.jsonl` returns
`unsupported-development-format` and preserves every byte. There is no importer,
converter, dual-write route, truncation, or adjacent recovery file. Any other
invalid version-2 content returns `invalid-response-outcome-bundle` without
repair or provider use.
Version 2 identifies the envelope and atomic publication format, not semantic
validity. An old replacement transition without an earlier eligible basis, an
invalid basis or artifact relation, a wrong-attempt reconciliation, or a
conflicting reservation fails closed before acquisition, reread, or write. The
runtime does not append retroactive evidence, continue an admitted successor,
or migrate, erase, or silently repair the history.

The runtime validates the complete retained semantic history before
acquisition, revalidation, reconciliation, or another provider-capable action.
Every record kind and variant participates. All owner, intent, epoch,
validation, attempt, outcome, carry-forward, retry, reconciliation, follow-up,
replacement, and response-identity references must resolve with the required
ordering and cardinality. Envelope integrity alone is insufficient. A malformed
or unsupported record blocks the whole bundle with zero provider calls.

`INTENT.json` carries these schema-v1 fields:

| Field | Required value |
| --- | --- |
| `schema_version`, `intent_key` | `1` and the caller's durable immutable key |
| `intent_kind` | `ordinary`, or `follow_up` with `predecessor_outcome_id` |
| `admitted_epoch`, `source` | Complete acquired epoch and one exact member of its `sources` |
| `operation` | `create_inline_reply` or `create_pull_request_conversation_comment`, selected from source kind |
| `placement` | Inline: `kind: review_thread`, `thread_node_id`, and `root_comment_database_id`; top-level: `kind: pull_request_conversation` and `pr_number` |
| `writer` | `identity`, `contract: portable-github-markdown-authoring`, `contract_version: 1`, selected `field`, and `body_sha256` of its exact UTF-8 bytes |
| `authority` | `decision: authorized`, `evidence_id`, and verified `actor_login` |
| `classification` | `result: human_feedback` or `automated_feedback`, and its `evidence_id` |
| `adjudication` | `disposition: respond` and the supporting `evidence_id` |
| `independence_evidence` | Explicit `available` evidence ID or `not_applicable` reason |

An exact unchanged pending intent crossing a new observational epoch adds
`carry_forward` with `from_epoch_id`, the complete `to_epoch`, and typed
`independence_evidence` whose assessment is `unchanged`. Schema 1 cannot express
a replacement.

Replacement caller schema 2 contains exactly `schema_version`, fresh
`intent_key`, `intent_kind: ordinary`, `replacement_basis_id`, and
`classification_artifact`, `adjudication_artifact`, `authority_artifact`, and
`writer_result_artifact`. Each artifact wrapper contains exactly
`canonical_utf8_base64`, `byte_length`, and `sha256`; its decoded bytes are
canonical JSON with the common basis, terminal-record, epoch, scope, operation,
and placement fields. Adjudication binds the classification digest, authority
binds both earlier decision digests, and the writer result binds all three plus
writer identity, contract, field, and an exact body-byte wrapper. The separate
body file must equal those bytes. Caller-selected epochs or routes,
noncanonical or extra fields, predecessor artifacts, stale or consumed bases,
and label-only freshness fail before provider access.

The runtime validates these bindings and reacquires provider evidence. It does
not adjudicate feedback or manufacture authority from an evidence identifier.
The semantic owner must supply a current decision and the already-written body.
Keep the selected policy evidence with that writer result.

The CLI uses `gh` against `github.com`. Its global `--gh-command-json` option
selects an explicit compatible argv prefix for controlled-provider qualification.
The program, local authority evidence, state directory, and authenticated caller
are trusted local inputs; this interface is not a hostile-same-user boundary.
