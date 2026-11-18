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
operations. A release's pipeline stage, calculated issue progress, description,
resource links, and release notes are distinct surfaces. Read the pipeline's
actual stage meanings instead of assuming an issue workflow's status applies.

Use the description for a concise plain-text summary and the release note for
formatted content. Check the selected field's current limits from its live
declaration or validation response; keep longer prose in the note rather than
truncating required content or relying on Markdown rendering in a summary field.

Capabilities can differ by surface. A connector may expose stage, version,
source commit, timestamps, and notes without resource-link or release-delete
operations. Prefer a supported connector operation for native release resources.
When it is absent, inspect the supported API or the release's UI controls for
adding a document or link. Select the permitted alternative with the same
scope and prepare the destination URL and a useful title where supported.
With either control, apply the link in step 5 below and check in step 6 that
the resulting resource opens the intended release or guide; a URL string in
the description does not establish a native link. Report a remaining capability
gap precisely. Missing connector support is neither permission to invent a
field nor evidence that the whole product lacks the operation.

## Reconcile state, content, and associated work

Each change follows the same order: prepare it (steps 1 to 4), refresh the
record and write the change (step 5), then confirm the result (step 6).

1. Match the Linear release's version and source to the published release.
   Use observed timestamps for actual events; preserve estimated dates as
   estimates. If the source commit and publication ref differ legitimately,
   explain their relationship instead of silently replacing one with the other.
2. Select the stage that expresses the verified outcome in the actual
   pipeline's terms. The release's accepted completion boundary says what it
   must reach; the pipeline's own stage meanings say which stage states what
   it has reached. A completed publication may coexist with unfinished
   installation or adoption work. Keep that work visible with its owner and
   next action; do not close issues merely to make a percentage reach 100. If
   the pipeline represents a broader outcome, stop at the stage that outcome
   has reached and explain the completed publication within it. Return a
   stage choice for decision only when it is genuinely unresolved.
3. Identify the native release resources that will link the tracked release
   to its forge page and maintained current installation guide, with further
   verification links as useful. Use the
   [presentation procedure](release-presentation.md) to author notes from the
   accepted changes and evidence. Existing GitHub or Linear prose is an input
   to assess, not a quality standard to copy. Keep both surfaces factually
   consistent while adapting their layout and audience.
4. Reconcile the finite graph applicable to this release as outcomes arrive:
   release and note, selected issues and their checklists, milestones,
   projects, initiatives, parents, children, dependencies, and dependents.
   Follow connections whose requirements or evidence affect the release, or
   whose tracked state changes with its result. Deduplicate visited entities;
   stop at unrelated branches and record why they do not apply. For each
   applicable entity, identify its outcome, owner, evidence, and smallest
   needed change to notes, descriptions, states, dates, checklists, release
   associations, relationships, or completion progress. Retain genuine open
   work and future-release scope, its accountable owner, and next action.
   Prepare association corrections within the authorized scope and preserve
   ownership when work moves to an existing successor. Use current native
   relations where required; do not assume GitHub issue sync carries Linear
   Release objects, notes, milestones, or blockers. Keep private account
   identities and operational evidence in their owning records; use aggregate
   coverage and appropriate public references in public tracking.
5. Refresh the affected record immediately before writing to it. When a field
   has changed, preserve the other contribution and prepare the change again
   from the current value; send an unresolved conflict to its owner. Then
   apply only the prepared change. An uncertain write stays unresolved, as
   described below; prepare again only a field proven unapplied and still
   authorized.
6. Read back every changed field and entity across the applicable graph,
   including descriptions, resource links, note content and coverage, stages,
   source/version, dates, checklists, relationships, and associations when
   changed. Verify actual propagation across the affected surfaces; a synced
   issue body does not prove its relations propagated. Check rendered
   headings, tables, and navigation as a reader would, including the displayed
   release timestamp. A successful write response alone is not completion.

Retain the submitted note text, but compare its readback by facts, required
actions, scope, and working link targets. Linear may normalize Markdown or
replace a forge PR URL with its corresponding Linear review URL. Check that
the replacement identifies the intended review and opens it correctly. Such
presentation changes do not require byte equality with the authored Markdown;
changed meaning or a wrong destination still needs correction. Artifact and
checksum verification retain their own exact-byte requirements.

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

When the selected outcome includes internal installation and use, invoke the
[internal rollout procedure](internal-plugin-rollout.md) for its named
accounts and harnesses. Publication and tracker reconciliation alone do not
establish that rollout; keep its actual results and outstanding owners visible.

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
