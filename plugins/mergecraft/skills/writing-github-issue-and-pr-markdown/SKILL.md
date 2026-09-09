---
name: writing-github-issue-and-pr-markdown
description: Use whenever directly drafting, writing, or editing the exact Markdown source of a GitHub Issue or pull-request body, conversation comment, submitted-review body, review-thread root, or review-thread reply, including edits to selected spans of an existing body. For a complete pull-request title and navigable description, use writing-reviewable-pr-descriptions, which consumes this contract. Do not use for repository Markdown files, read-only inspection, posting unchanged text, reactions, thread resolution, review submission, or other GitHub actuation.
---

# Writing GitHub Issue And PR Markdown

## Contract

Own the valid GitHub Flavored Markdown and the exact body value for one or more covered fields. Read and apply [the canonical authoring contract](references/authoring-contract.md) before drafting or editing any body.

This skill grants body-authoring authority only. It does not post or edit a GitHub object, submit a review, reply, react, resolve a thread, or perform an Issue or pull-request lifecycle operation. An operation-specific caller must establish any separate actuation authority.

## Workflow

1. Bind each requested covered field, the body-authoring intent, all applicable repository and consumer instructions, whether the body is new or an edit, and the caller's exact handoff format.
2. For an edit, obtain the exact current body and an explicit disposition for every span: retain byte-for-byte, replace, or remove. Do not infer permission to change a retained span.
3. Compose compatible instructions with the canonical contract. If an instruction materially conflicts, identify the conflicting requirements, state which applicable policy must be clarified or changed before authoring can resume, and stop without returning a candidate body.
4. Bind the line-ending sequence and terminal-newline state. Draft valid GFM while preserving structural newlines, explicit hard breaks, literal or opaque regions, and retained spans exactly as the canonical contract requires.
5. Compare the complete candidate with the bound preimage and dispositions. Reject accidental normalization, reflow, deletion, or changes outside the authorized spans.
6. Return the complete exact body in the caller-bound format with an unambiguous body boundary. If the caller requests only a JSON string, emit that string as the entire response: no Markdown fence, preamble, suffix, or separate metadata. Its decoded value is the body, including its bound line endings and terminal-newline state. In formats that permit explanatory text, state that newline binding outside the body boundary; a caller that already fixed it does not need an added restatement. If the response channel cannot carry the exact value, use a caller-approved lossless artifact or escaped display; otherwise stop rather than claim exactness.

For multiple requested fields, keep their body boundaries independent. Never concatenate bodies or let one field's terminal newline become another field's structural separator.
