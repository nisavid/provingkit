# Commit-message workflow facts

The frozen sources establish commit preparation and format requirements, but they do not verify a separately replaceable semantic-review step.

## Prescribed preparation and checks

Versionkeeping's `checkpointing-and-publishing-git-work/SKILL.md:24-36,63-79` requires a Git baseline, applicable verification, destination commit-policy establishment before the first commit, a literal-path task-only commit, and final verification bound to that immutable commit. It requires checking committed paths and preservation of unrelated index contents. Artifact review is outside this skill's ownership (`SKILL.md:11-20`); these passages do not prescribe a distinct semantic review of a drafted message.

Its `references/commit-policy.md:3-15` requires reading destination contribution guidance and linked commit rules, recording the policy source and DCO requirement, and resolving conflicting or unavailable policy. A policy can be reused while unchanged. The procedure adds no sign-off requirement where none exists. The supplied `CONTRIBUTING.md` contains no DCO requirement; this bounded read does not establish every possible external policy.

Repository `CONTRIBUTING.md:20-31` requires linking the owning issue or decision, updating canonical source, preserving member boundaries, using Conventional Commits, and reporting checks actually run. `AGENTS.md:47-58` requires Conventional Commits and whitespace checks, and prescribes validation for the touched surface. It describes Cocogitto commit-msg and pre-push hooks installed through `cog install-hook --all`. `cog.toml:1-7` maps those hooks to `.hooks/commit-msg.sh` and `.hooks/pre-push.sh` and sets `ignore_merge_commits = true`. Configuration establishes the named paths, not installed-hook state, script contents, or runtime semantic behavior; those are outside the frozen inputs.

## Supplied bounded witness

The supplied task-evidence artifact `commit-preparation/own-commit-observation.md:3-7` reports creation of commit `9a85baa9785b7d12c98bd652d037819ea4d9d38f` with subject `docs(research): record remaining hook acceptance bars`. It reports checks of document bytes, the initially empty index, configured email, staged paths, and whitespace, followed by a literal-path, one-document commit. The reported output includes Cocogitto parsing type `docs` and scope `research`, successful one-file commit creation, and subsequent committed-byte and whitespace checks.

This is a coordinator witness report, not an independently inspected native trace or controlled trial. It establishes neither a distinct semantic-review activity nor its absence, internal reasoning, isolated token cost, or replaceability. A missing separate tool call cannot settle those questions.

## Meaning for the accepted comparison

`docs/superpowers/research/2026-10-02-jev-axi-remaining-family-acceptance.md:20-25,45,58-61` distinguishes materially misleading claims or omissions from accurate concise summaries. Enumeration, stylistic preference, subject polish, and Conventional Commits formatting are separate purposes. A prescribed review requirement is insufficient evidence that a removable review step occurs.

The same record requires a useful effect in a native task and actual removal of verified review work for a replacement claim (`:80-97`). It requires establishing native message writing and review, whether a separate review exists, commit-msg-time context, and observable costs before the comparison (`:121-126`). Source inspection cannot pass runtime cases (`:52-56`).

## Smallest remaining observational gaps

A passive native preflight would still need to observe:

- The actual message-writing and review sequence, including evidence distinguishing any separately replaceable review activity from drafting.
- The message and intended committed scope available at commit-msg time, including staged versus unstaged coverage and any omitted or truncated context.
- The active hook/configuration identity and delivered check result for that episode.
- Which drafting, review, context-preparation, and check costs are observable; unmeasured components remain unknown.

These are factual gaps, not a proposed experiment or a behavior assignment. The accepted record authorizes neither a new native episode without a concrete accepted execution contract nor creation of review work solely to make it replaceable (`:9-10,101-117,121-126`).

All seven frozen input SHA-256 digests matched before and after this bounded read-only research. No workload, hook, network/provider call, source execution, file write, or delegation was performed.
