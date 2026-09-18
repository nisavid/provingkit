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
2. Choose exactly one publication-review mode and an explicit sorted specialist
   inventory before invoking the writer or freezing the candidate. `required`
   needs an absolute Task Witness bundle root and a current, nonhistorical,
   bare-clean Tricritical terminal projection. `not-required` needs no bundle
   and records no witnessed
   review provenance; it does not waive ordinary independent review.
   Pass the selected mode and specialists to
   [Writing Reviewable PR Descriptions](../writing-reviewable-pr-descriptions/SKILL.md)
   for the validated pair, authorized surface, and manifest from the pushed diff.
   When the writer's review gate applies, require its verified bare `clean`
   hand-back for the same candidate, review input, requirements, selected
   scopes, and current evidence dependencies. Rerun affected review on drift;
   preserve nonclean terminals as blockers. The helper's successful validation
   does not prove that this ordinary review ran. A suspected credential in
   either live or candidate PR text blocks before mutation; never echo,
   preserve, or republish it.
3. Let the helper resolve and prove the canonical private receipt root before
   mutation, then invoke one owned operation. Production CLIs expose no receipt
   root override; internal test and controlled-migration APIs may supply one.
   Stop on drift, ambiguity, receipt-storage failure, or unexpected final state;
   never retry/rollback automatically. Re-read identity, text, and state; inspect
   live rendering after structured changes.

Every create, text, and ready API/CLI call must supply `--review-mode` and
`--selected-specialists` as a JSON array, including `[]`. There is no default or
downgrade. Required mode is an optional witnessed route. When selected, it invokes the
authenticated Task Witness front door and requires its current evidence and the
registered Tricritical producer chain; if those are unavailable, stop before
mutation. The ordinary `not-required` route does not depend on Task Witness.
Carry the selected mode and specialist inventory unchanged through creation,
text publication, and readiness. A changed selection requires a newly frozen
candidate and fresh applicable review. A ready-only call must still have the
writer's current review hand-back when its review gate applies. If a resumed
task cannot verify the ordinary observations, require a new review or separately
qualified retained evidence; a publication receipt alone does not prove them.

Fixture-level witnessed-review coverage does not establish live publication
reachability. Do not infer a production claim from fixtures.

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
