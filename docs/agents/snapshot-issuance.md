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

The explicit cloud-member route below keeps that Kit identity while recording
separate delivered versions for selected members. Ordinary preparations and
unaffected member stamping retain the synchronized behavior.

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

## Preserve an installed cloud member floor

Use this branch when a selected cloud entry needs a prerelease delivery above
its independently installed version. It uses the same issuer, state, publication
barrier, complete-slate projector, and variant retention. Do not initialize another
authority or change an issued record. The supported comparison is the issuer's
SemVer precedence subset: normal numeric releases and dot-separated prerelease
identifiers, with no build metadata. A prerelease of `1.0.0` sorts below stable
`1.0.0`; appending build metadata does not supply an increasing version.

Before actual allocation, the operational owner binds the selected member,
installed floor, product source, Kit identity, provider comparison, and receiving
entry. Only affected entries need that evidence. The source examples use invented
versions and establish no provider acceptance or account enrollment. If actual
provider ordering conflicts with the supported rule, stop that delivery and
return the concrete incompatibility to the versioning owner.

Record the member's floor and named-release interval in the existing state:

```json
{
  "operation": "configure-cloud-member",
  "member": "versionkeeping",
  "floor": "1.0.0",
  "target_release": "1.0.1",
  "preceding_cut": "1.0.1-0",
  "next_named_release": "1.0.1-alpha.1"
}
```

Then submit `{"operation":"prepare-cloud","request_id":"cloud-delivery-1",
"source_commit":"<full source commit>","members":["versionkeeping"]}`.
The response uses `provingkit-cloud-snapshot-preparation-v1`. Its ordinary
`version`, interval, and sequence still identify the Kit snapshot. Its
`cloud_members` map records each selected member's floor, interval, consumed
sequence, and delivered version. Pass the exact response bytes to the existing
`--snapshot-record` projector interface. For the invented interval above:

```text
1.0.0 < 1.0.1-0.snapshot.1 < 1.0.1-0.snapshot.2 < 1.0.1-alpha.1
```

Each selected member has a persistent reservation sequence and last-issued
version. Gaps survive cancellation, reentry, and a Kit retarget; resetting the
Kit's sequence does not reset member sequences. Identical preparation requests
recover the original record. Changing their source or member selection is
refused. A new configuration cannot lower a floor or rewind an interval. Consume
the recorded successor to advance a member cut; close its normal target by
naming that normal release in both cut fields before moving to a higher normal
target and its `0` anchor. Member transitions share the pending-exposure barrier
and named-cut coordination with Kit transitions.

Projection stamps selected members' copied manifests, adapters, and applicable
catalog entries with their member versions; other members use the Kit version.
The complete slate remains required. The receipt's `delivery.version` and
generation path remain Kit identities; `delivery.cloud_members` retains the exact
member records, and the preparation digest binds both to the same source.
The owner selects the affected cloud entries from this projection and verifies
that all entries being updated use their applicable floor records. An ordinary
preparation or an omitted member is not a floor-aware cloud update.

Use the existing `issue` operation and reviewed publication plan. Immediately
before exposure, its transaction compares the prepared Kit interval and member
configurations with current state and checks both issuance high-water marks.
A stale floor or member interval rejects issuance. A pending or uncertain
attempt blocks new issuance and member transitions. Reconciliation, cancelled
attempt retention, withdrawal, and target additions use the original operations;
adding a variant keeps the original Kit/member preparation and existing bytes.
Redelivery exports retained bytes without allocating an increasing cloud update.
The receiving owner must check their suitability before using them.

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
Cloud examples also inspect projected member/catalog identities, reject wrong
expected versions despite successful execution, and pass a real projector
receipt through synthetic issuance and retained-byte recovery. These checks
do not establish provider comparison, preserved cloud enablement, or useful loading.
The clock example replaces Python's `time.time`; it does not change the host
clock. Synthetic source identifiers test identity independence, not Git age.

Before actual delivery, require current independent review, authoritative state
custody, selected-route and named-cut participation, and recovery evidence at
the first-exposure boundary. The installation owner then qualifies the selected
client with useful earlier and later source selections, without runtime markers
or unrelated edits. Provide the reviewed revision, both delivered versions,
source commits, original complete receipts, exact projected and packed bytes,
mode inventories and digests, ordering/retry/variant outcomes, pinned transport
identities, and publication/readback results. Record the owner's procedure
revision and naturally useful invocation; installed use is complete only when
the selected client actually loads the changed copy under its new identity.

Before live cloud use, require clean Daybreak review of the final implementation
and relevant dependencies. The receiving owner verifies the actual member's
increasing identity, corrected content, preserved enablement, and useful loading,
recording the procedure revision used. Source checks and source merge do not
complete those receiving criteria.
