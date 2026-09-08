# GitHub Issue And Pull-Request Markdown Authoring Contract

## Covered fields and authority

This contract applies to the human-facing GFM body of each of these fields:

1. Issue body.
2. Issue conversation comment.
3. Pull-request body.
4. Pull-request conversation comment, represented by GitHub as an IssueComment.
5. Submitted-review body.
6. Review-thread root.
7. Review-thread reply.

The semantic writer owns valid GFM and the exact body bytes, including line endings and terminal-newline state. Coverage grants only authoring authority. It does not grant authority to post or edit a body, create an Issue or pull request, submit or dismiss a review, create a review thread, reply, react, resolve a thread, approve, request changes, or perform another GitHub operation.

## Applicable instructions and conflicts

Apply compatible repository, consumer, and field-specific instructions together with this contract. Tone, required headings, vocabulary, disclosure, and stricter content or security rules normally compose when they do not change the source-shape, preservation, or exact-body requirements. A rule that forbids emitting unsafe content composes by blocking authoring, not by silently rewriting a retained span.

A conflict is material when satisfying another instruction would require wrapping or reflowing a flowing-prose block, using an implicit source newline for an intended hard break, normalizing line endings or terminal-newline state, changing a retained or opaque span, making the posting actuator rewrite the body, or exceeding the granted authoring or actuation authority. Report the conflicting requirements and fail closed without a candidate body. Do not silently choose one contract, weaken a protected clause, or describe a conflicting result as compliant.

## Source shape

Within each flowing-prose block, emit the entire block on one physical source line and leave visual wrapping to GitHub. Keep structural newlines between blocks and container members. This is one line per flowing-prose block, not one line for the whole document or container.

Apply the rule recursively inside lists, blockquotes, details, callouts, and comparable nested structures. A container can have many structural lines; every flowing-prose block within it still occupies one physical line.

Represent an author-intended hard break inside a flowing-prose block with an explicit `<br>`. Column-width wrapping, a trailing-space hard break, a backslash hard break, and editor reflow do not satisfy this contract.

Retain the source shape required by literal, raw, control, and opaque regions. These regions include fenced and indented code, tables, raw HTML, preformatted content, machine-owned control markers, and externally supplied opaque text. Do not parse or reformat such a region merely to apply the flowing-prose rule.

## New, replaced, and retained bytes

Apply the source-shape rule only to newly authored or replaced flowing-prose spans. Preserve every retained span byte-for-byte, even when legacy content wraps, uses mixed line endings, lacks a terminal newline, or otherwise differs from the rule. Do not opportunistically normalize, reflow, repair, or reinterpret unrelated historical content.

Before composing an edit, bind an exhaustive ordered disposition of the current body into retained, replaced, and removed spans. Reassemble those spans in that order without a generic Markdown parser. If the requested edit cannot be made without guessing a boundary or changing retained bytes, stop for clarification.

Choose exact line endings and terminal-newline state before authoring. For an edit, preserve them wherever their bytes are retained and follow the explicit replacement instruction for new bytes. For a wholly new body, follow an explicit repository or caller choice; when none exists, use LF line endings and no terminal newline. Do not perform Unicode, whitespace, or newline normalization after assembly.

## Exact-body handoff

Return or hand off the complete body as one exact value, separate from explanatory text. Preserve every character from the first body byte through the terminal-newline state. When a display medium cannot preserve that value, use a caller-approved lossless artifact or escaped display and label it as a representation rather than the posting payload; otherwise report that exact handoff is unavailable.

An operation-specific actuator receives the writer-produced body as opaque data. It may encode the surrounding transport request but must not parse, reflow, normalize, repair, decorate, or otherwise rewrite the body. Posting and exact reread verification belong to that separately authorized actuator, not to this authoring contract.

This contract introduces no generic Markdown parser, automatic reflow, historical-post repair, response routing, semantic outcome envelope, receipt transport, or GitHub actuation framework.
