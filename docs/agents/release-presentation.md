# Prepare a useful release presentation

Give readers the release's value, the right downloads, and a complete route to
installation or update. Use this procedure when preparing or revising release
notes, asset links, or the linked guide. Private installation and source-only
development do not invoke release presentation by themselves.

## Ground the release story

Read the accepted release scope and its actual cumulative changes. Bind the
Slate and member versions, supported targets, exact asset names and checksums,
source commit, tag or published ref, release destination, and the evidence for
their correspondence. A documentation revision can differ from artifact source;
explain that relationship when it matters to the reader.

Identify the audience, its previous usable state, and what this release lets it
do differently. Trace each material claim to a change record, reviewed source,
or observed result. Distinguish a shipped capability from a plan, source checks
from client acceptance, and documented controls from actions actually observed.
Keep unknowns explicit while preparing a draft; plausible details cannot fill
missing evidence.

The release owner supplies scope and artifact facts; the semantic writer turns
them into useful prose. The publisher checks the assembled result and performs
authorized publication. Existing [release boundaries](../release-boundary.md)
and the owning workflow govern those operations. A writing procedure does not
grant publication, installation, account, or signing authority.

## Compose for the reader

Start from the [release body template](../releases/release-body-template.md),
adapting its sections to the actual release rather than preserving empty
headings. Keep the accepted downloads-first presentation: a concise statement
of the release's value and status, useful downloads, and a discoverable complete
upload/update guide precede the detailed changes.

Organize the changes around what users can now do, what became more reliable,
and what they need to change. Group related work into coherent capabilities;
explain a technical change through its practical consequence. Include a short
example when it materially helps a reader use the capability. Attribute the
right member or component without forcing readers through internal task IDs,
raw commits, or the sequence of agent handoffs. Link reviewable detail where it
helps, and retain source attribution for adopted work.

State required upgrade actions and compatibility limits near the changes they
affect. Give meaningful limitations enough prominence to guide a decision;
keep test counts and maintainer execution detail in linked verification
evidence. A release note is not the full changelog or a proof transcript.
Describe the supported product and its boundaries without implying that every
unfinished development task is a limitation of the released capability.

Derive the download rows from the frozen Slate and asset inventory. Label
targets in terms readers can choose and pair archives with the checksum files
listed in that inventory. When the frozen inventory establishes that no
checksum file exists, provide an inline archive hash verified against the
frozen inputs. An unavailable download does not establish absence; resolve
missing or conflicting checksum evidence before publication. Distinguish
installable artifacts from forge-generated source archives.
Maintain one [installation and update guide](../install-and-update.md) for the
current release. Link its stable published path from release notes and the
repository's human entrypoint. Update the method when it changes; do not create
a guide per version or retain older installation routes as supported choices.
Keep version-specific filenames, hashes, and upgrade changes in the release's
assets and notes. Record the reviewed guide revision in the publication evidence.

Write the guide for someone installing plugins: short steps for installation,
update, and loading, with only useful troubleshooting. Keep account-specific
observations, past validation results, pending qualification, release-upload protocols, and
agent coordination requirements in their owning maintainer records. State only
user-relevant limitations in the guide. Verify instructions against provider
documentation and applicable observations; neither source alone establishes a
successful installation.

Use `proseweaving:writing-for-people` to write and edit the release notes and
installation guide. Name archives `provingkit-<plugin>-<version>.zip` for
Agent Plugins clients and `provingkit-<plugin>-<version>-claude.zip` for the
Claude projection. Name each checksum file `<archive>.sha256`; its filename
entry and digest must match the archive in the release inventory.

For GitHub and Linear, use the same verified semantic inputs and retain one
maintained authoring source for the release. Adapt presentation to each
surface, preserving facts, scope, required actions, and important limits.
Assess existing notes against these criteria before reusing them.

## Review and publish

Freeze the candidate text and its source/evidence identities. Check that every
selected reader-facing deliverable is present or has an explicit operator
disposition. An unpublished draft or a generic limitations paragraph cannot
stand in for the promised guide. Verify asset names, target/version, checksum
correspondence, guide revision, relative links and anchors, and the complete
rendered reading journey. Follow fragment links to their actual rendered
destinations; a heading does not by itself establish an anchor. Use the
repository's applicable independent review
for the final candidate, including changed agent-facing instructions.

Review meaning as well as mechanics: a valid link does not establish complete
instructions, and a change list does not establish a useful release story.
Resolve every valid finding that changes the accepted release outcome. Broader
changelog automation, version arithmetic, and future platform qualification
remain separate unless the selected release actually depends on them.

The authorized publisher loads this procedure and records its reviewed source
revision. Publish through the owning release workflow, then read back the
public body, selected downloads, their checksum files or inline hashes, and
guide. Verify their identities, exact archive-to-hash correspondence, and
navigation against the frozen inputs. Retain partial outcomes and resolve
uncertain writes before repeating them.

Before reporting closeout, invoke
[Linear release reconciliation](linear-release-reconciliation.md) for the
corresponding tracked release and notes. That procedure owns stage, association,
link, and readback mechanics; it does not rewrite semantic content implicitly.
If the release has no Linear representation in scope, record that fact rather
than creating a pipeline or integration without a requirement.

Return the published release and guide URLs, input identities, the actual
review and readback results, Linear disposition, and any remaining owner/action.
Record first use of this procedure separately from drafting or static checks.
Publication does not by itself prove installation or complete every related
issue.
