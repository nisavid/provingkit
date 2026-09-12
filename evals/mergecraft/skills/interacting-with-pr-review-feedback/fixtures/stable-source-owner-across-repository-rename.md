# Stable source owner across a repository rename

A verified pull request starts at `base-owner/base-repo#7` with stable typed
repository and pull-request identities, number 7, an inline review comment
source, and one exact source revision. The repository is renamed or transferred
to `renamed-owner/renamed-repo`; the stable typed identities, source kind,
source identity, source revision, and pull request number remain unchanged,
while repository coordinates, links, head/base OIDs, and head repository are
mutable context.

The first ordinary intent writes one `PullRequestReviewComment`. A fresh
ordinary key for the same exact source revision is attempted after the rename.
A terminal predecessor then needs a replacement. Its old locator no longer
resolves, so replacement preparation must receive and validate a freshly
acquired current repository locator before publishing a basis or authoring a
successor. An unresolved or mismatched locator stops before provider access.
After the current locator resolves, the replacement basis retains the new full
context, reuses the predecessor owner, and runs complete prewrite validation.

State the stable owner decision, provider-write decision, replacement
acquisition prerequisite, and final binding behavior. Keep
`PullRequestReviewComment` for inline replies and `IssueComment` for pull
request conversation comments. Preserve separate ordinary, follow-up,
independent, retry, reconciliation, and replacement authority.
