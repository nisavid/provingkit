# Reconcile a published release with Linear

Keep the release people can obtain and the release people track consistent.
Use this procedure after publication, after a change to a release's content or
scope, and when reconciling stale Linear release records. The publisher runs
it before reporting release closeout. Ordinary source development does not
trigger it.

This is Provingkit's repository-carried Linear release procedure. The
[tracker contract](issue-tracker.md) governs issue operations; the
[presentation procedure](release-presentation.md) owns the reader-facing prose.
Use `capturing-agent-procedures` when changing either workflow. Publishing a
release, qualifying an installation, and updating a tracker establish different
outcomes; retain each outcome's actual authority and evidence.

## Establish the release and the intended change

Read the selected release's accepted scope and the current forge and Linear
records. Bind the repository, forge release identity and URL, tag and source
commit, version, publication time, Linear pipeline and release identity, note
identity and covered releases, and associated issues. Compare the tag's actual
target with any recorded source rather than treating a branch name as an
immutable revision. Distinguish published, draft, prerelease, withdrawn, and
future planned releases; a chronological list alone does not select the current
release or authorize cleanup.

Identify the fields and operations needed to reconcile that scope. Reuse an
existing matching release and note; if identity is ambiguous, resolve it before
creating a duplicate. Preserve unrelated fields, other releases, and other
owners' issue work. Record the public/private audience of each destination
before moving content between them.

## Choose the available controls

Discover the connected Linear capabilities and inspect their current input
contracts. Prefer the supported release, release-note, and issue-association
operations. A release's pipeline stage, its calculated issue progress, and its
release notes are distinct surfaces. Read the pipeline's actual stage meanings
instead of assuming a status label from an issue workflow applies to releases.

Capabilities can differ by surface. A connector may expose stage, version,
source commit, timestamps, and notes without an external-link field or a
release-delete operation. Use an explicit forge-release link in the supported
description or note when that supplies the needed navigation. If a native
association or action is required, inspect the supported API or UI before
declaring it unavailable. Use the permitted alternative with the same scope
and verify its result; report a remaining capability gap precisely. Missing
connector support is neither permission to invent a field nor evidence that
the whole product lacks the operation.

## Reconcile state, content, and associated work

1. Match the Linear release's version and source to the published release.
   Use observed timestamps for actual events; preserve estimated dates as
   estimates. If the source commit and publication ref differ legitimately,
   explain their relationship instead of silently replacing one with the other.
2. Set the stage according to the release's accepted completion boundary and
   the pipeline's meaning. A completed publication may coexist with unfinished
   installation or adoption work. Keep that work visible with its owner and
   next action; do not close issues merely to make a percentage reach 100.
   If the pipeline represents a broader outcome, preserve its unfinished stage
   and explain the completed publication within it.
3. Supply useful navigation between the tracked release, its forge page, and
   the applicable guide or verification evidence. Use the
   [presentation procedure](release-presentation.md) to author notes from the
   accepted changes and evidence. Existing GitHub or Linear prose is an input
   to assess, not a quality standard to copy. Keep both surfaces factually
   consistent while adapting their layout and audience.
4. Reconcile the release's selected issues and actual dependencies. Retain
   genuine open work and future-release scope. Correct mistaken associations
   within the authorized scope, and preserve ownership when work moves to an
   existing successor. Use current native relations where required; do not
   assume GitHub issue sync carries Linear Release objects, notes, or blockers.
5. Refresh the affected record immediately before mutation. Apply only the
   prepared change, then read back the release, note content and coverage,
   links, stage, source/version, dates, and changed associations. Check the
   rendered note and navigation as a reader would. A successful write response
   alone is not completion.

When a write times out or its result is uncertain, inspect the intended
post-state and relevant activity before deciding whether anything remains to
do. A matching result needs no replay. Conflicting or incomplete observations
keep the affected operation unresolved; use the smallest supported read or
escalate the concrete gap rather than blindly repeating writes. Preserve
successfully completed independent operations.

## Apply an authorized retention action

Keep release deletion separate from ordinary lifecycle reconciliation. Read the
applicable retention policy or the current instruction and enumerate its exact
release identities before acting. Establish whether it covers hosted release
entries, assets, tags, tracker records, or any combination: these are different
objects and can have different deletion effects. Preserve the current release,
planned future releases, and objects outside the selected scope.

Resolve any missing destructive scope before deleting. Within a clear grant,
apply only that scope and verify both the removals and the retained objects.
For an uncertain deletion, observe its outcome before any further attempt.
An authorized cleanup of older releases is one action unless an explicit
standing policy makes it recurring. Do not generalize it into automatic
deletion of release history.

## Close the loop

Return the forge and Linear release URLs, note URL or identity, observed
lifecycle and issue-progress disposition, source/version correspondence,
readback result, and any remaining owner/action. Distinguish reconciled tracker
state from publication, installation, and consumer acceptance. A meaningful
remaining gap stays visible in the owning work, rather than disappearing into
an otherwise completed release report.

When this procedure is first adopted or changed, record the reviewed source
revision the release agent loaded and the actual invocation and output checks.
Exercise stale-stage, missing-link, stale-note, uncertain-write, and planned
future-release cases; exercise deletion only within its actual grant. Check
discovery through the release caller separately from the correctness of the
steps. A prepared reference or static link check is not evidence of consumer
use or a continuously running synchronization service.
