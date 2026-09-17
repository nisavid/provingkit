---
name: writing-reviewable-pr-descriptions
description: >-
  Use when creating or changing a GitHub PR title and/or body, including draft,
  stacked or Graphite, publication, summary, media, diagram/atlas,
  access-note, caveat, or preservation-sensitive work. Do not use for read-only
  inspection, comments, checks, threads, or merge-only work with unchanged text.
---

# Writing Reviewable PR Descriptions

## Contract

A PR body navigates change, verification, and remaining work.

[Publishing Reviewable PRs](../publishing-reviewable-prs/SKILL.md) owns forge
actuation. This skill owns the complete pair, bounded by requested surface.
Generated forge text is no substitute.

## Routing

- For an unpublished title/body proposal in chat, use this writer only.
- For PR creation or stored title/body mutation, the publisher invokes this
  writer and then owns forge actuation.
- For an existing PR's isolated relation-ledger edit, use the bounded mode below,
  including historical PRs. Normal creation and canonical publication retain
  the navigation workflow.
- For a ready-only request, the lifecycle caller routes to the publisher. The
  publisher consumes the current writer-owned validated pair and manifest but
  sends no text mutation.
- Read-only inspection, comments, checks, base changes, labels, and merge-only
  work use their own owners; neither this writer nor the publisher is a generic
  PR router.

## Relation Applicability

Before freezing new or materially changed Issue contributions, use
[Maintaining Issue–PR Relations](../maintaining-issue-pr-relations/SKILL.md).
Reuse a supplied qualified plan and include its ledger intent in this candidate;
do not restart discovery or publication. Unchanged intent, incidental mentions,
and unrelated text edits need no relation reads. Return pending bilateral or
native work to the caller after the candidate is published.

## Existing Relation Ledger

Use this mode only for an authorized Issue–PR ledger span in an existing PR.
Read [the ledger contract](references/relation-ledger.md) and the
[GitHub Markdown authoring contract](references/github-markdown-authoring.md).
Bind stable repository/PR identity, exact live title/body/state, one UTF-8 span,
and its authorized replacement. Return the complete title/body pair and ledger
manifest; preserve title and every body byte outside that span. The validator
proves this derivation and checks sensitive content. It does not infer semantic
relations or authorize the edit.

This mode requires no surviving branch or reconstructed Diff navigation and
establishes no readiness claim. For normal creation or canonical publication,
include the ledger in the workflow below. A lifecycle caller that needs
canonical publication evidence must use that route after any isolated edit;
a ledger receipt cannot satisfy its audit. A detected closing reference outside
the authorized span needs a separately scoped content request.

## Workflow

1. Bind repository, PR, pushed SHAs, head repository/owner, and draft state; read
   instructions/template.
2. Immediately before editing an existing PR, read its live title/body as the
   preservation preimage and bind `body-only`, `title-only`, or `title-body`.
   Description/body means `body-only`; title-only preserves body byte-for-byte;
   creation requires the full pair. Stop rather than widen ambiguity. Treat any
   suspected credential in the live or candidate body as a hard security gate:
   never echo, preserve, or republish it. Require authorized removal and, when
   exposure is plausible, rotation before publication can continue.
3. Resolve the exact pushed base and head plus their unique merge base. Compute
   reviewer-visible statistics from merge base to head while retaining the base
   tip in PR identity and immutable comparison links. For stacks bind every
   member, base, dependency, order, title, URL, and per-PR diff.
4. Read the generated
   [GitHub Markdown authoring contract](references/github-markdown-authoring.md),
   compose it with repository and consumer instructions, and stop on a material
   conflict. Then read [the body contract](references/body-contract.md) and
   draft its smallest complete reviewer path. Read
   [change navigation](references/change-navigation.md)
   and build its leading collapsed Stack then Diff for stacked PRs, or Diff for
   standalone PRs. Start that prefix at byte zero with exact full-line
   disclosure tags, and use a truly empty source line between Stack and Diff and
   before any suffix. Treat the suffix as opaque bytes. Stop if the pushed diff
   is unavailable.
5. Create their versioned content-addressed review-input manifest, binding
   identity, pushed refs/OIDs, title/body digest, Diff rows, stack, and all
   baseline-fragment dispositions. For an existing body, use the shared
   `change_navigation.bot_body` helper to separate recognized trailing bot
   blocks. Seal and exhaustively partition only the authored live prefix;
   derive the candidate from those fragments. The publisher retains the latest
   live bot tail separately. Keep opaque authored content after the navigation
   prefix byte-for-byte unless its change is explicitly authorized. Use the
   publisher PR-number token for create.
   For diffs over 100 files, additionally bind the first 100 deterministic local
   Git target paths, omitted count, and immutable comparison URL; render only
   those rows plus the canonical omission record. Smaller bodies remain complete
   and every published body, including its retained bot tail, stays at or below
   65,536 characters.
6. Validate the complete pair and prove the candidate is the exact ordered
   derivation of its sealed baseline fragments. This local proof does not show
   that the claimed baseline is the current live PR; the publisher separately
   binds unauthorized fields to its immediate live preflight:

   ```bash
   python3 skills/writing-reviewable-pr-descriptions/scripts/validate_change_navigation.py \
    --repository OWNER/REPO --pr NUMBER --title "TITLE" \
    --git-repository /absolute/path/to/clean/worktree \
    --review-input /absolute/path/to/review-input.json /absolute/path/to/pr-body.md
   ```

7. For large, stacked, cross-cutting, reviewer-heavy, or readiness-ambiguous
   text, invoke the imported `review-loop` operation (`tricritical:loop`) on the
   exact candidate title/body bytes. Give
   the loop explicit authority to mutate only those bytes, no forge or source
   authority, and require a bare `clean` receipt. Revalidate the resulting pair
   and review-input manifest. Any other terminal blocks return or publication.
8. Compare to the live baseline for loss and prove the candidate is the exact
   ordered fragment derivation, including unchanged suffix line endings and
   final-newline state; return the complete validated title/body pair,
   authorized text surface, and review-input manifest. Unchanged is validated,
   not authorized.
   Do not mutate the forge or verify stored/rendered state from this skill.

Use local data only when `HEAD` equals PR head. Recompute after push,
base/stack change, or linked-title change.

## Validation And Extension Boundary

This standalone validation proves manifest, body, and local Git
self-consistency; it does not prove the live pull request identity. The
publisher or a separately supplied live observer must independently bind
repository, PR, base tip, head, and stored preimage before publication.
Fragment derivation proves the candidate follows the manifest's claimed
baseline; it does not make that baseline a current forge observation.

The manifest's `content_sha256` detects content drift; it does not authenticate
the manifest's source, caller, or authority. Noncurrent Stack rows remain
caller-supplied observations until an external stack adapter re-observes them.
Only the current row is reconciled with the sealed Diff.

This skill validates supplied navigation. It has no deterministic body
generator, pathname classifier, Stack-discovery adapter, GitHub observer, or
GitHub Action. Callers supply categorized rows and independently observed stack
topology. The local Git observer uses deterministic target-path order and makes
no GitHub Files-order claim; a future observed-order adapter needs a versioned
interface.

The navigation implementation recognizes only the strict leading Stack/Diff
prefix. It must not grow a homegrown CommonMark/GFM scanner for the opaque
suffix. Follow the parser scope guard in `references/change-navigation.md` even
when a review loop proposes broader fence, list, link, table, or HTML state.

The first-100 presentation is a file-count bound, not a body-size guarantee.
Schema v3 has no second truncation path. If the canonical bounded body still
exceeds 65,536 characters, stop instead of dropping or shortening more rows.

## Visual Escalation

Use the smallest diagram that materially shortens review. Only after
visual-escalation selection, use an atlas when static views cannot keep
architecture, chronology, and source routes legible. Ordinary PRs do not require
atlas previews.

Then read [the atlas design](review-atlas-reference-design.md). Keep atlas source,
tests, docs, manifests, and generated assets outside application repositories.
Only PR-body links/private attachments are outputs on the review surface.
Protected deep links may rely on destination access control, but never embed
bearer or signed credentials. Preserve canonical Stack/Diff and current custom
content.

Then read the optional [atlas extension contract](references/review-atlas-extension.json).
Resolve only its default path. Load a regular non-symlink overlay only for exact
scope; absence continues public core. It may add instance data/stricter policy,
never weaken, widen, or redefine. Ignore/report conflicts; public core wins.

## Finish

Apply the hard rules and acceptance checklist in `references/body-contract.md`.
When readiness, approval, merge, deployment, release, or closeout language
depends on authority, state the repository/operator boundary inline and stop on
an unresolved owner. This writer remains the content and validation owner.
