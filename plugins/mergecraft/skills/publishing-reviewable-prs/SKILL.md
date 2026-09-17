---
name: publishing-reviewable-prs
description: Use when standalone GitHub PR creation, canonical title/body/draft-ready publication, publication-evidence audit, or evidence reconciliation is required, including fork-sync and fixup PRs. Do not use for generic PR inspection, comments, checks, threads, or merge actuation.
---

# Publishing Reviewable PRs

Own standalone creation and canonical text/readiness after transport.
`versionkeeping:checkpointing-and-publishing-git-work` owns commits/pushes;
Graphite first creates stack draft transport.
[Writing Reviewable PR Descriptions](../writing-reviewable-pr-descriptions/SKILL.md)
owns the `pr-content` operation: the complete title/body pair and its authorized
text surface.
Preserve unauthorized fields byte-for-byte. Helpers preflight, mutate once,
reread, then atomically store a redacted local receipt. The publication lease
serializes only cooperating processes that share the same local receipt root;
it does not serialize another machine, user, bot, automation, or GitHub actor.
GitHub provides no conditional write, so the read-write-reread sequence can
race and the reread cannot prevent an intervening lost update.

## Routing

- Chat-only title/body proposals use the writer without this publisher.
- Creation and stored title/body changes use this publisher, which invokes the
  writer for the complete validated pair and manifest.
- Ready-only work uses this publisher with the current writer-owned pair and
  manifest; it never rewrites text as part of readiness.
- Generic read-only inspection, comments, checks, labels, base changes, and
  merge-only work use their own owners. Publication audit is the publisher's
  narrow read-only exception.

## Workflow

1. Bind repository/base, qualified head, head repository/owner, pushed OIDs, PR,
   and remote commits. Read policy/templates; retain live title/body/draft
   preimage immediately before edit.
2. Use [Writing Reviewable PR Descriptions](../writing-reviewable-pr-descriptions/SKILL.md)
   for the validated pair, authorized surface, and manifest from the pushed diff.
   Choose exactly one publication-review mode and an explicit sorted specialist
   inventory before freezing the candidate. `required` needs an absolute Task
   Witness bundle root and a current, nonhistorical, bare-clean Tricritical
   terminal projection. `not-required` needs no bundle and makes no clean-review
   claim. A suspected credential in either live or candidate PR text blocks
   before mutation; never echo, preserve, or republish it.
3. Let the helper resolve and prove the canonical private receipt root before
   mutation, then invoke one owned operation. Production CLIs expose no receipt
   root override; internal test and controlled-migration APIs may supply one.
   Stop on drift, ambiguity, receipt-storage failure, or unexpected final state;
   never retry/rollback automatically. Re-read identity, text, and state; inspect
   live rendering after structured changes.

Every create, text, and ready API/CLI call must supply `--review-mode` and
`--selected-specialists` as a sorted, unique JSON array of nonempty UTF-8
strings, including `[]`. Parse it through the bounded strict JSON reader before
publication; malformed input receives one value-free classification. There is
no default or downgrade. Required mode is an optional witnessed route. When selected, it invokes the
authenticated Task Witness front door and requires its current evidence and the
registered Tricritical producer chain; if those are unavailable, stop before
mutation. The ordinary `not-required` route does not depend on Task Witness.

## Inspect Publication Failures

Treat a nonzero mutation exit as a command rejection and a mutation timeout as
an unknown outcome. Report only the publication stage, return code or timeout,
approved classification, and value-free next checks. Command output, command
inputs, request data, PR title/body bytes, and tracebacks remain private because
they may contain credentials or other sensitive data. Without separately safe
evidence, state that the rejection cause is unknown.

The `subprocess.run` boundary spans process launch and communication, so every
`OSError` leaves process start unknown and, for a mutation, target outcome
unknown. Report a fixed, value-free read or mutation classification, and retain
the original exception only as internal causality.
Validate command arguments and encode input inside the typed process boundary. A
local command preparation failure proves that no process started and, for a
mutation, no target mutation ran. Retain its cause without exposing input values.

Accept successful helper output only after strict UTF-8 decoding. Treat
malformed successful read output as unavailable and malformed successful
mutation output as an unknown outcome. A nonzero exit remains a process failure;
retain its return code without decoding or disclosing its output. Candidate
validation is local: identify the validation stage and give value-free checks
for candidate structure, review-input binding, local runtime availability,
trusted executable ancestry, and temporary-directory availability. Do not route
local validation failures to forge authentication or read-access advice.
Local body and review-input failures use fixed classifications. For create,
text, ready, and reconciliation, name the local input class and direct the
operator to its path, permissions, UTF-8 encoding, or exact-candidate
regeneration without displaying an exception, key, path, or request value.
Retain the original exception only as internal causality. Keep this local
guidance separate from forge authentication and access checks. Admit review
input and any supplied body before validator execution, forge access, receipt
store preparation, or receipt writes; later exact candidate and live-state
binding remains mandatory.
Parse provider PR URL suffixes as positive, bounded ASCII decimal through the
shared parser. Its digit bound follows the supported Python runtime's integer
conversion boundary, not a universal GitHub API limit. Classify an oversized
JSON integer as invalid JSON and retain the conversion failure as internal cause.

Admit live observations before any comparison, hash, serialization, index, or
display. Required fields use exact JSON scalar types and valid UTF-8; the PR
number and canonical URL number must agree. Validate either supported head
repository shape before indexing it. Retain provider extensions as detached
JSON values within the shared depth and item boundary; finite JSON numbers and
ordinary extensions keep their existing meaning, and ignored extensions gain
none. Classify duplicate keys, non-finite constants or exponents, oversized
integers, excessive nesting, and non-JSON direct values without their data.
REST recovery normalizes only a null body to empty text; it preserves strings
exactly and classifies every other body type as malformed.

After either failure, independently reread the exact PR state once. For an
admitted reread, report whether the observed state matches the exact intent, the
preimage, or another valid state. Classify an unavailable reread separately. The
failed helper and observed relationship mint no canonical receipt. Preserve the
original safe command diagnostic and reread classification; no automatic retry
or rollback was attempted. Any later recovery reuses existing read authority
while it remains valid; obtain new authority only if the target or action is
outside its scope. A later mutation still requires authority for that mutation
and cannot upgrade the failed helper write to a causally proven transition.

When a mutation exits zero but its verification reread fails, preserve the
publication stage, zero-exit fact, safe reread classification, and original
reread cause. Write no canonical receipt, and do not retry or roll back.
A zero-exit mutation followed by a nonmatching valid reread retains the observed
preimage or other-state relationship without assigning causality. The unchanged
preimage does not prove that the intended state was never stored. Write no
canonical receipt, and do not retry or roll back.

After a verified mutation, build the CLI acknowledgement from the reloaded
canonical receipt inside the same failure boundary. A missing receipt or failed
reload, summary, or serialization leaves publication unacknowledged: report a
value-free failure, independently audit exact state, and do not retry.

Keep private body snapshots behind the same value-free boundary. A creation,
write, or flush failure is local preparation and proves that no mutation ran. A
cleanup failure after a zero-exit mutation triggers the normal exact reread but
mints no canonical provenance or receipt; inspect state and do not retry. When
cleanup fails while another publication error is active, retain that publication
error and keep the cleanup exception only as internal causality.

Fixture-level witnessed-review coverage does not establish live publication
reachability. Do not infer a production claim from fixtures.

Audit direct readers through the same admission boundary. Translate ordinary
callback exceptions to `AuditResult(status="unavailable")` without converting
their values to text; retain the authoritative latest receipt when available.

When the optional witnessed route is used, Task Witness remains a cooperative
validator integration. Harness sandbox and approval controls remain the
ordinary execution authority; Mergecraft makes no descendant-containment claim.

## Create

Use `scripts/create_reviewable_pr.py` with exact identity, existing absolute
review-input, and an absolute template containing
`__PUBLISHING_REVIEWABLE_PRS_PR_NUMBER__` wherever the assigned number belongs.
In new-PR Stack review input, use it only for the sole current row's number and
same-repository URL; never use it in an existing or noncurrent row.
Preserve original template bytes and perform token-only rendering; never
reverse-replace an assigned number. It validates sentinel rendering,
rejects a matching PR, and creates one nonce
draft. Recover only when one draft matches nonce and all identity/text.
If the recovery read fails, retain both its safe classification and the original
create failure as the cause; perform no additional mutation and write no receipt.
Never display a provider-reported URL in a failure; construct any displayed PR
identity only from a display-safe validated repository and positive PR number.
Malformed zero-exit create output, including an invalid PR identifier, follows
that same one-read nonce recovery path and never mints provenance by itself.
After local preparation failure, broad process failure, nonzero exit, timeout,
or malformed zero-exit output, retain the exact process fact and classify the
one nonce recovery observation as empty, nonmatching, multiple-exact, or
unavailable. Local preparation failure proves that no process started and no target mutation ran.
A broad process failure leaves process start and mutation outcome unknown.
A unique exact match preserves the existing continuation, but
does not prove that the errored command created it.
Every terminal failed or unverified transition states that canonical provenance
was not minted, no canonical receipt was written, and no automatic retry or
rollback was attempted.
Validate assigned-number rendering, publish once, exact-reread, write a canonical
receipt, and leave draft.
The reviewed candidate remains the token-bearing pre-number candidate. After
GitHub assigns a number, prove the body is its unique token-only rendering,
validate the same evidence again, and perform one final exact nonce-state reread
immediately before the single canonical edit. That post-review reread is the
receipt preimage.

## Update Existing PR Text

Capture the live title SHA-256 and the SHA-256 of the authored body prefix,
using the shared `change_navigation.bot_body` helper and any already sealed
baseline digest to preserve the exact boundary, then run `scripts/update_reviewable_pr.py text`
with exact identity/OIDs, state, absolute body/manifest paths, and authorized
`body-only`, `title-only`, or `title-body`. Never default broad. It privately
snapshots validated bytes, proves unauthorized fields unchanged, and publishes
once. The GitHub command sends only the authorized field or fields. Classify an
unchanged candidate as `no-op` before invoking the updater. That workflow
terminal is not updater success and never mints a transition receipt; use the
read-only audit when publication evidence is required. The updater rejects any
no-op that reaches it. Preserve current custom content, exact-reread, and write
a canonical receipt. For a new PR created through
Graphite transport, pass the original token-bearing `--body-template`; the
publisher performs the sole token substitution after Graphite assigns the PR.
In either review mode, reread the exact live preimage after validation and block the
write if the authored portion changed. Hosted review integrations may append
recognized bot-owned blocks to the body after review-ready publication. Treat
those blocks as opaque retained content: compare the authored prefix, reread
the latest live suffix immediately before mutation, and publish the new
authored prefix followed by that suffix. A bot-only suffix change is not
publication drift; an unrecognized or authored change remains a drift gate.

## Mark Existing Draft Ready

After readiness/rendering gates, refresh preimage and run
`scripts/update_reviewable_pr.py ready` with exact identity/OIDs, digests, draft,
and manifest. It validates then immediately preflights. Error plus exact intended
state remains causally ambiguous and receives no canonical receipt; do not retry.
Only a zero-exit mutation followed by an exact final reread receives a canonical
receipt.

The ready operation can consume the token-bearing review-input manifest produced
for a new PR. Pass the original token-bearing body template with
`--body-template` when the numbered body cannot be derived uniquely. The publisher
checks that the rendered authored body and manifest digest match the template, binds
the transition to the canonical creation receipt for the same repository, base,
head, title, review mode, and specialist set, and then records only the numbered
ready transition. Repeating a verified ready transition is a receipt-backed
no-op; it never sends a second ready command. If the PR is draft again after a
canonical ready transition, the creation manifest cannot authorize another
transition; use fresh numbered review input. Select the transition from a fresh
live preflight under the receipt lock so a concurrent publisher or draft change
cannot reuse stale readiness state.
In either review mode, reread the exact live draft after validation and before
the ready mutation; identity, title, authored body, and draft state must remain
unchanged. Retain the latest recognized bot tail.

## Receipts, Audit, And Reconciliation

Receipts form an ordered append-only ledger per stable repository/PR number.
Ordered identity epochs retain historical base/head OIDs while requiring the
authoritative latest receipt to match the current complete identity. Their strict,
versioned schema binds sequence and predecessor/content hashes, the exact
last validated preflight observation and final reread, identity/OIDs, title/body
and review-input SHA-256 digests, state, publisher/policy/schema versions,
operation, timestamp, and provenance—never title/body bytes or credentials.
Schema-v4 body digests cover the authored portion of the resulting body;
historical schema-v2/v3 receipts retain complete-body digest semantics.
Author-drift checks compare only that authored prefix, while the final
transition check retains the latest recognized bot suffix in the stored body.
Because GitHub provides no conditional write, a receipt does not prove the
server-side mutation preimage or exclude a lost-update race. Canonical v4 receipts
record either explicit `not-required` or `required`; required also binds the
canonical publication-candidate digest, Task Witness launch-envelope digest,
anchor generation/active record/trust/bundle, and Tricritical manifest/projection
digests. V2-only ledgers remain `legacy-unrecorded`; any decrease in receipt
schema version invalidates the ledger. Reconciliation records
`unwitnessed-reconciliation` and never mints review provenance.
Write them atomically only after the helper's exact final reread. A storage
failure after a verified mutation is not a reason to retry the mutation: inspect,
then reconcile if appropriate.

The canonical root is
`$XDG_STATE_HOME/mergecraft/pr-publication-receipts`, falling back to
`~/.local/state/mergecraft/pr-publication-receipts`. Helpers prepare a private,
writable store and hold an exclusive per-PR lease from final preflight through
mutation, reread, and append. Standalone creation cannot address the per-PR
ledger until GitHub assigns a number, so it first holds a head/base creation
lease and proves the store, then prepares and locks the exact ledger before the
canonical edit. These local leases coordinate only publishers using the same
receipt root; they cannot create conditional or atomic GitHub actuation. The
chain detects accidental gaps, forks, swaps, timestamp
rollback, reordering, and edits; it is not a cryptographic security boundary
against a hostile process running as the same user.

Use `scripts/audit_reviewable_pr.py audit` with the same exact identity and
receipt root before resuming or closing a publication task. It reads only the
authoritative latest receipt and returns `verified`, `drift`, or `unavailable`.
At ledger admission, admit every retained receipt string and object key as UTF-8
scalar text before reconstruction or canonical encoding. Reject escaped lone
surrogates as a value-free receipt error. When ledger admission fails, audit
returns `unavailable` before the live reader and leaves receipt storage unchanged.
Only a complete, structurally valid live PR observation reaches receipt
comparison. Valid identity, text, and state differences are drift. Invalid JSON,
duplicate or non-finite JSON, and incomplete or malformed fields are unavailable.
Required observation strings must be exact UTF-8-encodable Unicode scalar text
before comparison, hashing, or serialization. Preserve admitted text without
normalization or replacement; classify a lone surrogate as malformed.
An unavailable live read retains its safe parse, schema, launch, timeout,
return-code, UTF-8, or unknown classification in `reason`; it remains an ordinary
audit read, not a post-mutation verification.

Use `scripts/audit_reviewable_pr.py reconcile` only after independently
confirming exact live identity/state and supplying the bound `--review-input`.
It validates the first read, requires the second live reread to preserve
identity, title, authored body, and draft state, retains its latest bot tail, and
refuses when the authoritative latest receipt already matches. Otherwise it may
append one permanent `reconciled-unreceipted` receipt even when older canonical
receipts exist. It performs no forge mutation and can never upgrade that
provenance to `canonical`; a later actual canonical transition gets a new
receipt.

## Hard Rules

- Never use raw PR create, title/body edit, or ready commands or connectors.
- `--head` must use `OWNER:BRANCH`; its owner must exactly match
  `--head-owner` and the owner of `--head-repository`.
- Resolve OIDs/digests from live pushed/stored state immediately before mutation.
- Scan both title and body, live and candidate, for suspected secrets before
  mutation or reconciliation; never echo matched bytes.
- Only Graphite transport may be temporary; repair it before handoff/review.
- Required review binds the exact repository, PR number or create token,
  base/head/OIDs, title, raw body-source bytes, published UTF-8 body, review
  input, publication profile, and specialist inventory. Never substitute raw
  and published digests or review a numbered create candidate.
- Treat the required-review supervisor as cooperative bounded liveness, not an
  arbitrary-process containment boundary. Never infer descendant quiescence
  from ordinary successful completion.
- File inputs must be existing absolute literal paths, never variables, `~`,
  relative paths, substitution, stdin, or inline multiline content.
- Never use a repository-local receipt root. An explicit absolute override is
  reserved for tests and controlled migration. Never copy receipts into a
  repository, PR, issue, comment, log, or attachment.
- Never describe unpushed changes or discard current custom content.
- Stop when base, stack membership, preservation, or authority cannot be
  established safely.

## Completion Evidence

Report URL, base/head OIDs, title/body digests, state, receipt id/provenance/
sequence, audit or result status, checks, and remaining action. Comments,
feedback, CI, merge, and Git/ref publication retain distinct owners; the bundled
comment helper is internal.
