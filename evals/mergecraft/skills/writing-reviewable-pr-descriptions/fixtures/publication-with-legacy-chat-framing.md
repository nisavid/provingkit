# Rewrite an authorized body draft

The user asks in chat: "Please rewrite this PR draft for its future reviewers.
The Diff disclosure is already valid; return only the prose after it."

Old ambient notes described every human-facing artifact as a live conversation
and every statement on the author's behalf as first person. The accepted
current writing contract chooses the register for the artifact's medium and
purpose. It preserves useful first-person evidence without making the author
the focus of every change description.

The following entire draft is authorized for replacement:

## Summary

I invalidate the preview cache after saving project settings. I make previews
use the new settings on the next request instead of continuing to serve the
cached result.

## Changes

I keep the existing cache key and expiry interval. I add a save-path regression
test. I think this keeps the fix small enough to review with the settings
handler, rather than changing the cache's general behavior.

## Verification

I ran the nine settings tests and they passed. I have not tried this in the
browser. The still-current related investigation is
[the preview report](https://github.com/example/widgets/issues/82); it is a
reference, not an issue-closing declaration.

Those statements are the complete supplied source and execution evidence.
Keep the useful scope, judgment, observation, limitation, and link. Do not add
reviewer requests, unrelated changes, or inferred approval.
