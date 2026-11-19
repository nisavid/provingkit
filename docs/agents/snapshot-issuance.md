# Issue increasing snapshots and retain delivered bytes

Prepare changing Provingkit copies with a distinct delivered version, then
record their immutable source and artifact identities before publication.
Directly loaded working source keeps its source version, including the
next-normal-release `X-trunk` marker. This procedure uses the existing
[artifact projector](../release-artifact-projection.md) and
[ad hoc publisher](../ad-hoc-artifact-publication.md).

Use `capturing-agent-procedures` when producing or consuming this procedure.
The consumer records the reviewed implementation and procedure revision before
dependent work. Use `checkpointing-and-publishing-git-work` for the existing
Versionkeeping publication planner and executor; this issuer never pushes.

## Supported boundary

The implementation is a local cooperating-caller mechanism for the synchronized
seven-member Provingkit release unit. It supports Agent Plugins, Claude, and
Cursor projections, full SHA-1 source commits, normal targets, and numbered
`alpha`, `beta`, and `rc` cuts. A variant is one target's complete-slate archive,
original receipt, and mode inventory. The issuer binds these three files; the
projection and packing owners qualify their contents and modes.

SQLite serializes callers sharing one state file. Local CLI tests establish
that boundary, including competing processes, recovery through another
process, and state-path confinement during an ancestor swap. They do not
establish shared custody, participation by another clone or route, provider
object visibility, or installed client behavior.

Before live use, the delivery owner establishes one authoritative state path,
its custody owner, and every selected-route issuer's participation. Named-cut
owners must coordinate their consumed-cut records through that same owner and
state. Keep snapshot issuance and cut publication mutually exclusive until the
owner has recorded the cut transition. Git compare-and-swap alone cannot make
an unrelated publisher update this state. If another publisher can consume a
cut or expose a snapshot without participating, the live ordering claim remains
unqualified and exposure stays held.

Qualify state retention and recovery under that owner: retain the database,
pending request, original reviewed plan, original executor result if available,
and artifacts through process and custody changes. Use SQLite's backup API or
quiesce the issuer before copying its database and any active journal. A copied
or restored older database must not become a second issuer. Initialization is
only for a release unit with no prior snapshot state; inventory existing
exposures and reservations before choosing its current interval. Existing
issuance history requires its original state or an explicitly reviewed
migration, rather than another empty database.

## Version and identity

The spelling names the preceding cut:

```text
0.1.0-alpha.7 < 0.1.0-alpha.7.snapshot.1
              < 0.1.0-alpha.7.snapshot.2 < 0.1.0-alpha.8
0.1.0-alpha.8 < 0.1.0-alpha.8.snapshot.3 < 0.1.0-beta.1
0.1.0-rc.2.snapshot.4 < 0.1.0 < 0.2.0-0.snapshot.1 < 0.2.0-alpha.1
```

The numeric `0` anchor is an ordering sentinel before the target's first cut.
The intended successor is in the preparation record. Sequences continue
across cuts within one normal target. No clock or source-commit ordering
contributes to the sequence. Gaps are retained. Build metadata is not a delivery
identity on this route.

The issuer retains full source identity and the exact archive, receipt, and
mode bytes for each recorded variant. A fresh snapshot can use an unchanged
source commit. Source or existing-variant changes require another version,
including after withdrawal. An added target preserves the original source
and every existing variant. Already issued older versions remain available for
explicit redelivery; that operation leaves the issuance high-water mark alone.

## Prepare and project

Run the reviewed issuer from its own clean checkout. Its product source may be
an older clean checkout. Every invocation receives a JSON request and emits one
JSON response; rejection exits nonzero and includes a reason.

```sh
python "$PROVINGKIT_ISSUER_SOURCE/scripts/prepare_snapshot_issuance.py" \
  --state "$PROVINGKIT_ISSUANCE_STATE" --request "$PROVINGKIT_ISSUANCE_REQUEST" \
  > "$PROVINGKIT_ISSUANCE_RESULT"
```

The state file needs an existing parent owned by the current user with no
group or other permissions. Below the filesystem root, each ancestor must be
owned by the current user or the host root identity and must not be writable by
other users unless it is a sticky directory such as `/tmp`. The issuer rejects
symlinked ancestors except for a root-identity-owned system alias directly below
a non-writable filesystem root, such as a host's `/tmp` or `/var`. It opens the
database through a pinned parent descriptor; platforms without no-follow
search-capable directory operations or descriptor-backed paths are unsupported.
These checks exclude other local users, not processes running with the current
user's authority.

The database is local operational state, outside the source checkout and
transport branch. Once its custody is qualified, initialize it with a request
shaped as follows, using the existing publisher's reviewed endpoint fingerprint
and the owner's current cut:

```json
{
  "operation": "initialize",
  "custody_owner": "selected-delivery-owner",
  "endpoint_fingerprint": "sha256:<64 lowercase hexadecimal digits>",
  "target_release": "0.1.0",
  "preceding_cut": "0.1.0-alpha.7",
  "next_named_release": "0.1.0-alpha.8"
}
```

Prepare using `{"operation":"prepare","request_id":"delivery-1",
"source_commit":"<full source commit>"}`. Retain the exact successful stdout
as `PROVINGKIT_SNAPSHOT_RECORD`; it is the projector's preparation input.
An identical request recovers that record. Reusing a preparation identifier
with another source, or preparing under a target addition's identifier, is
rejected without reserving another number. Preparation reserves a number; it
grants no exposure.

Project each selected target with the complete slate and the same preparation:

```sh
python "$PROVINGKIT_ISSUER_SOURCE/scripts/build_release_artifacts.py" \
  --source "$PROVINGKIT_PRODUCT_SOURCE" --channel main --target claude \
  --snapshot-record "$PROVINGKIT_SNAPSHOT_RECORD" \
  --output "$PROVINGKIT_PROJECTION_ROOT/claude"
```

The projector stamps copied manifests, generated adapters, and the applicable
catalog. The receipt preserves the product commit, identifies the actual
projector revision, and records the delivered version and exact preparation
digest. Source manifests remain unchanged. Partial-slate snapshots are refused.
The existing dotfiles installer does not accept snapshot receipts: their
additional `delivery` field and independently identified projector revision
require a separately reviewed consumer update. The selected isolated native
Codex marketplace consumer remains subject to its own qualification.
Complete the owning projection checks, mode checks, and packing procedure before
constructing a publication commit. Use the versioned generation
`ad-hoc/<source-commit>/<delivered-version>/<target>/`; retain older paths.

## Record where the source stands before first exposure

Ivan selected this rule on 2026-11-19; the record is the "Source standing,
settled on 2026-11-19" section of
[the versioning contract decision](https://github.com/nisavid/provingkit/issues/1075).
It governs first exposures made after those selections were recorded. This
guidance calls no earlier delivery compliant or not.

Before a snapshot's first exposure, its delivery record holds three things:

- The review of its source commit, or a statement that there is none.
- Whether the commit is on the release line, with the `main` commit it was
  tested against.
- When it is not, the ticket that lands the commit or withdraws the copy, and
  the named remote ref, which is kept, that holds the commit.

A record that states no review also names the channels it permits. After a
landing, the record gains the landing note described below.

Delivery from source that is not on the release line needs this record and no
approval of its own. A snapshot whose record states no review goes only to the
channels its record names and carries the same landing or withdrawal ticket.
Client probes of draft work do not wait for a review. Each installation still
needs Ivan's authorization, and the request to him states the review status.

The issuer does not yet hold or check any of this: its `prepare` request takes
a request name and a source commit, and its state has no place for the record.
Until it does, whoever issues the snapshot writes the record, retains it with
the preparation response, and provides it at handoff. Complete it before the
`issue` request below; that transaction does not check it.

**What counts as a review to name.** For a source commit on the release line,
name the reviews of the pull requests that changed what is delivered since the
preceding named release. For a source commit off the release line, name each
review of the difference between that commit and its merge base with the
release line, by the commit the review covered. A review of one part of that
difference is recorded as a review of that part. Where the parts were reviewed
and the combination was not, say exactly that; the snapshot is then treated as
having no review. The cases differ on purpose: on the release line every change
has passed that line's own review and merge, and off it the combination has
passed neither.

**How landing is recorded.** After a landing, the delivery record gains the
commit that landed the source and says whether the delivered source equals it.
The note changes no delivered identity. It is what lets "landed" survive a
squash merge, where the source commit itself never joins the release line.

**Release-line status by hand.** The release line is `main` on the canonical
remote, the GitHub repository `nisavid/provingkit`. A local `main` is not the
release line, and the projector's `--channel` argument is not evidence of the
status. The status comes from Git, not from an argument. Until the issuer
computes it, whoever issues the snapshot works in the checkout that holds the
source commit. First confirm that `origin` is the canonical repository itself,
not a fork or a similarly named repository: `git remote get-url origin` prints
exactly `https://github.com/nisavid/provingkit` or
`git@github.com:nisavid/provingkit`, with or without a final `.git`. Also
confirm that `git rev-parse --is-shallow-repository` prints `false`. Then test
the source commit against one fetched `main` commit and record that commit:

```sh
git fetch origin main &&
  main=$(git rev-parse --verify 'refs/remotes/origin/main^{commit}') && {
  git merge-base --is-ancestor <source commit> "$main"
  echo "status=$? main=$main"
}
```

Record the exit status together with that `main` commit:

| Exit status | Meaning to record |
| --- | --- |
| 0 | The source commit is on the release line. |
| 1 | The source commit is not on the release line. |
| Any other | The answer could not be established. |

Record "could not be established", never "not on the release line", for any
other status, when the commands print no status, when the fetch fails, when the
checkout is shallow, and when `origin` is not the canonical repository. Such a
record does not yet say whether the commit is on the release line, so the
snapshot's first exposure waits until a later check establishes it.

**What makes a remote ref kept.** [Ivan answered on 2026-11-19](https://github.com/nisavid/provingkit/issues/1075#issuecomment-7016813642):
a protected place. A named remote ref is kept when it sits under the name that
a repository rule protects from deletion, where delivered sources that are not
on the release line are pushed. A branch that can be deleted does not meet the
rule, and a written commitment on the landing ticket does not either. Until the
repository has that place and a ref there holds the commit, a commit that is
not on the release line does not meet the rule, and its first exposure waits.
Each push to that place needs its own authority.

The push that puts a delivered source into the protected place goes through the
Versionkeeping planner, as a create-only push. When the source is not at or
above the tip of some branch on the remote, for example a merged pull request's
head whose branch is gone, the plan is blocked. Such a blocked plan is not
restated as a plain push: the push stops, and Ivan decides on a one-time
exception for that exact push. This
paragraph grants no push and no exception. The [ticket that tracks the planner
change](https://github.com/nisavid/provingkit/issues/531#issuecomment-7018079892)
says why, and holds the change that would let the planner plan such a push.

## Commit issuance before the first exposure

Prepare and review the normal Versionkeeping publication plan for the immutable
transport commit. Immediately before its executor can transfer artifact
objects, submit an `issue` request:

```json
{
  "operation": "issue",
  "request_id": "delivery-1",
  "publication_plan": "retained/ready-plan.json",
  "reviewed_plan_sha256": "sha256:<reviewed plan digest>",
  "transport_repository": "transport-worktree",
  "variants": {
    "claude": {
      "artifact.tar.gz": "packed/claude/artifact.tar.gz",
      "RECEIPT.json": "packed/claude/RECEIPT.json",
      "modes.tsv": "packed/claude/modes.tsv"
    }
  }
}
```

The example binds one target. Include every target present in the transport
commit; the three-target packing recipe requires three entries. Extra
unrecorded snapshot files or variants in its outgoing history are rejected.

This transaction checks the stored current interval and last-issued position,
the original preparation, reviewed plan digest and destination, each variant's
source/version binding, and the immutable Git blobs across the reviewed plan's
complete outgoing commit set. Versionkeeping owns computation and revalidation
of that set. Every previously exposed variant must remain at the publication
tip unchanged. Intermediate snapshot files must also match an exposed or
currently issuing identity, even if they disappear before the tip.
It stores the artifact bytes, advances the issuance position, and records a
pending exposure together. A competing issuer or cut transition is blocked
until that pending request is reconciled. An earlier reservation cannot finish
after a higher version has advanced the position.

The ad hoc branch push is the first potential exposure. Provider visibility of
objects during an unsuccessful push requires its own observation; a failed push
does not prove that no exposure occurred. The qualified caller must execute
only the matching retained plan, once, after successful issuance. This CLI does
not launch or intercept Versionkeeping, so qualifying that caller ordering is
part of the route's completion criteria.

Keep the original executor result as bytes and submit
`{"operation":"reconcile","request_id":"delivery-1",
"publication_result":"retained/original-result.json"}`. A matching terminal
`verified` result with its required remote-ref postcheck settles exposure. A
conclusive original `blocked` result with `push_attempted:false` cancels that
attempt, consuming the version and retaining its bytes. Cancelled deliveries
are unavailable for redelivery. Preserve the original invocation's provenance;
a later unattempted result cannot describe an earlier uncertain attempt.
A matching attempted result with an incomplete verification postcheck is
rejected by the CLI, but its attempt observation and result digest are retained
durably. Exposure remains pending; a later unattempted result cannot clear it.

Cancelled unattempted generations keep their local records and bytes. Exclude
their unpublished commits from later publication ancestry by reconstructing
the next artifact-only change from the verified published tip or qualified
creation base, through Versionkeeping's normal ownership and ancestry checks.
Deleting their files at a later tip is insufficient: a push also transfers
the newly reachable historical commits.

For a cancelled target addition, keep its immutable recorded bytes and submit
a fresh `add-variants` request after reconstruction. A recorded target without
verified exposure remains eligible with those same bytes; the new request's
`retry_of` field links the cancelled attempts. The cancelled request stays
closed. Source, version, existing variants, and high-water position are
unchanged. An uncertain attempted addition remains pending and blocks this
retry path.

A lost response, attempted failure, missing result, or incomplete postcheck
keeps the request pending. Recover it with `{"operation":"inspect"}` or the
identical `issue` request. Retry recovers the original identity; it does not
authorize replaying a push. The existing publication owner reconciles the
original executor and remote outcome before retry or continuation. Do not
clear the hold by constructing a successful result or initializing new state.

## Extend, redeliver, and advance

| Operation | Request and result |
| --- | --- |
| Add a target | Use `add-variants` with a fresh `request_id`, existing `version`, matching `source_commit`, and the same publication fields and variant map as `issue`. At least one target must lack verified exposure. A recorded unexposed target requires its exact retained bytes. Existing bytes and the issuance position stay unchanged; reconcile the addition's own pending exposure. |
| Redeliver or roll back | Use `redeliver` with `version`, `target`, and a fresh `output` directory. It exports retained original bytes only for a variant with verified exposure. It leaves the last-issued position unchanged. |
| Withdraw | Use `withdraw` with `version`. The record and bytes remain retained. Explicit redelivery can still select those retained bytes; withdrawal cannot permit replacement. |
| Record a consumed cut | While the qualified owner excludes cut publication and snapshot issuance, use `advance-cut` with `preceding_cut` equal to the stored successor and the new `next_named_release`. Pending exposures block this operation. Stale preparations then fail issuance. |
| Close a normal target | Consume the normal release with `advance-cut`, naming that normal release in both cut fields. New preparations stop. |
| Start the next normal target | Use `retarget` with the higher `target_release` and its `next_named_release`. This requires a closed target and no pending exposure; it retains history and starts the new target's `0` anchor and sequence 1. |

After every uncertain result, recover the same state before choosing another
operation. Retain it while a version or recovery selection remains supported.
The issuer has no remote cleanup operation.

## Verify and hand off

Run `python -m unittest tests.test_prepare_snapshot_issuance
tests.test_build_release_artifacts` and `git diff --check` on the final
candidate. Issuer examples use local Git commits and constructed publisher
results; they do not establish a live Versionkeeping execution. Projection
examples execute the actual CLI and inspect emitted manifests and receipts.
The clock example replaces Python's `time.time`; it does not change the host
clock. Synthetic source identifiers test identity independence, not Git age.

Before actual delivery, require current independent review, authoritative state
custody, selected-route and named-cut participation, recovery evidence at the
first-exposure boundary, and the source-standing record above. No independent
review of the source commit is required; the record states its review or that
there is none. The installation owner then qualifies the selected
client with useful earlier and later source selections, without runtime markers
or unrelated edits. Provide the reviewed revision, both delivered versions,
source commits, the source-standing record, original complete receipts, exact
projected and packed bytes,
mode inventories and digests, ordering/retry/variant outcomes, pinned transport
identities, and publication/readback results. Record the owner's procedure
revision and naturally useful invocation; installed use is complete only when
the selected client actually loads the changed copy under its new identity.
