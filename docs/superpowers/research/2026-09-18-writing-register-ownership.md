# Writing register: source ownership and consumer boundaries

The writing correction spans Proseweaving's generic prose mechanics, Mergecraft's PR-specific framing, and the consumer's global instructions. The current source already assigns those owners, but conversation-specific rules remain in the generic skill, Mergecraft's planned Proseweaving route is absent, and the installed global Codex instructions differ materially from their maintained source.

This note supplies facts for [Settle medium-aware writing contracts and source placement](https://github.com/nisavid/provingkit/issues/109). It does not settle the replacement wording or authorize implementation, installation, source retirement, or historical-post repair.

## Evidence boundary

- Provingkit source: commit [`147e1ddfc969b5119001488ce1556627d3b2449b`](https://github.com/nisavid/provingkit/tree/147e1ddfc969b5119001488ce1556627d3b2449b), read on 2026-09-18 UTC. The research worktree began clean on this revision.
- First-party GitHub observations: the current bodies, comments, assignments, and native blockers of the related issues, plus the live example PR body. Issue and PR bodies are mutable observations, not immutable source evidence.
- Host scope: Hatchery only. Global Codex instructions and their dotfiles source were compared through targeted clause-presence checks. No private instruction bytes, machine-local paths, remote-host observations, or private configuration values are reproduced here.
- Source and host inspection was read-only. Map charting separately recorded native decision dependencies; it made no plugin, installed-skill, global-instruction, or PR-body edits. No behavioral evaluation or harness invocation was run; corpus inspection establishes coverage, not successful writing behavior.

## Requested behavior

The operator's request makes the document's subject the primary focus of publication-like writing. Change summaries should normally describe the change directly in the imperative, as commit messages do. First person remains useful for attributable investigation, verification, judgment, or uncertainty; it is not generally prohibited, including at an opening when the content warrants it. Chats and replies may retain conversational framing. Issue bodies need their own purpose considered: an investigation question, bug report, or decision proposal is not automatically a statement of an implemented change. [The map](https://github.com/nisavid/provingkit/issues/106) records the task boundary.

The live [example PR](https://github.com/nisavid/provingkit/pull/105) was observed at head `c458a9e3c6ba0970f4357e3d18e6227bf9743068`, with `updatedAt` of `2026-09-18T02:08:14Z`. After its required collapsed navigation, the narrative starts “I restore”; the Boundary section starts “I keep”; Provenance and compatibility starts “I bind.” These describe the change or its composition. Later, “I have not established the cause” attributes an evidence limit. That distinction supports the requested correction without treating every occurrence of “I” as a defect. The PR body was not edited.

## Current owners and gaps

| Surface | Current source fact | Boundary requiring attention |
| --- | --- | --- |
| Generic prose | Proseweaving's [README](https://github.com/nisavid/provingkit/blob/147e1ddfc969b5119001488ce1556627d3b2449b/plugins/proseweaving/README.md) owns portable human-facing prose mechanics and leaves personal voice to consumer-global instructions. The public skill is `proseweaving:writing-for-people`; there is no `writing-for-humans` skill in this revision. | Keep the correction in the existing portable skill rather than introducing a second generic writer. Choose what belongs in universally loaded mechanics versus conditional medium guidance. |
| PR descriptions | Mergecraft's [body contract](https://github.com/nisavid/provingkit/blob/147e1ddfc969b5119001488ce1556627d3b2449b/plugins/mergecraft/skills/writing-reviewable-pr-descriptions/references/body-contract.md) already says to lead with resulting behavior, write for an unfamiliar reviewer, and omit author effort. Its [writer](https://github.com/nisavid/provingkit/blob/147e1ddfc969b5119001488ce1556627d3b2449b/plugins/mergecraft/skills/writing-reviewable-pr-descriptions/SKILL.md) owns titles and bodies, while the publisher owns forge actuation. | Express PR change-summary framing at this surface owner and compose generic mechanics explicitly. Preserve required navigation at byte zero; the prose opening rule applies after that prefix. |
| Issue bodies and other GitHub fields | The [GitHub Markdown authoring contract](https://github.com/nisavid/provingkit/blob/147e1ddfc969b5119001488ce1556627d3b2449b/plugins/mergecraft/skills/writing-github-issue-and-pr-markdown/references/authoring-contract.md) covers seven distinct body fields, composes tone and field-specific instructions, and owns exact source shape and preservation. It does not prescribe a universal narrative register. | Keep publication-versus-conversation semantics separate from GFM bytes. Do not impose PR imperatives on every Issue body or conversational register on every covered field. |
| Review voice | Mergecraft's [README](https://github.com/nisavid/provingkit/blob/147e1ddfc969b5119001488ce1556627d3b2449b/plugins/mergecraft/README.md) explicitly records the missing review-voice route and use of ambient writing instructions meanwhile. Its [topology](https://github.com/nisavid/provingkit/blob/147e1ddfc969b5119001488ce1556627d3b2449b/plugins/mergecraft/topology.json) contains no Proseweaving call. | The existing review-voice producer owns the review ask ladder and projection. Installing Proseweaving alone does not implement this caller route. |

### Generic rules still carry conversation assumptions

The [current skill](https://github.com/nisavid/provingkit/blob/147e1ddfc969b5119001488ce1556627d3b2449b/plugins/proseweaving/skills/writing-for-people/SKILL.md) says it sets no voice and excludes composition of PR titles and bodies (lines 8–14), but its generic sections include:

- An opener framed around what a person just asked, said, or did, plus a finding tied to a backticked symbol (lines 22–38).
- Exactly one ask per comment and a review-severity ladder using “Could we,” “Please,” “Let's,” and first-person conviction (lines 49–55).
- Reviewer reply etiquette within Claim And Qualify (lines 57–66).
- Reply-specific rules for paragraphs, collapsed details, headings, and tables mixed with general document-shape guidance (lines 68–81).

The [edit pass](https://github.com/nisavid/provingkit/blob/147e1ddfc969b5119001488ce1556627d3b2449b/plugins/proseweaving/skills/writing-for-people/references/edit-pass.md) similarly treats an added second ask as a generic closing defect and tells every piece to sound like speech (lines 22–33 and 54–60). These are concrete scoping problems; they do not justify removing useful conversational advice.

The evidence guard also remains overbroad: the skill's lines 85–86 and [evidence reference](https://github.com/nisavid/provingkit/blob/147e1ddfc969b5119001488ce1556627d3b2449b/plugins/proseweaving/skills/writing-for-people/references/evidence-in-prose.md) prohibit asserting what a system does without a run, conflating source-supported behavior with an observed runtime outcome. The reference now has five guards, including Separate The System From The Setup, rather than the four assumed by the older split ticket. Preserve that newer distinction when reconciling its requested thinning.

### Corpus coverage does not yet establish publication register

The [seven-case behavior corpus](https://github.com/nisavid/provingkit/blob/147e1ddfc969b5119001488ce1556627d3b2449b/plugins/proseweaving/skills/writing-for-people/evals/evals.json) contains an operator stopping report, reviewer reply, three review comments, team-channel status, a release-note response to the operator, a review-comment edit, and a support-chat reply. The release-note case combines an entry with a question back to the operator. There is no standalone PR-body, Issue-body, article, or document-register comparison, and no paired case distinguishing an author-centered change summary from useful first-person evidence.

The [validator](https://github.com/nisavid/provingkit/blob/147e1ddfc969b5119001488ce1556627d3b2449b/scripts/validate_proseweaving.py) verifies fixture/corpus shape, executor/grader separation, projections, inventory, and content identity. Reading those checks does not demonstrate that agents choose the right register. The eventual producer needs behavior evidence that preserves natural conversational writing while changing publication framing.

## Global instructions and maintained source

The historical [global-writing port resolution](https://github.com/nisavid/provingkit/issues/22#issuecomment-5521832171) identifies `nisavid/dotfiles` as owner, `home/dot_codex/private_AGENTS.md.tmpl` as maintained source, and `tests/global-agents-policy.zsh` as its policy gate. Current local dotfiles source was read at commit `bad7fb140f39f93bf90679d9a9060e8fbb103a58`; the template was clean and its latest touching commit was `d984081aca89d3bf0940072e81f7a22f1b71405d`.

Targeted private observations establish the following without reproducing the instructions:

| Clause category | Maintained source | Installed global Codex instructions |
| --- | --- | --- |
| Conversation as the frame for every human-facing message | Present | Present |
| Deliverable leads with what it gives the reader | Present | Present |
| Personal voice and first-person judgment/evidence | Present | Present |
| Blanket first-person direction spanning chat, PRs, Issues, and documents | Absent | Present |
| Explicit source-supported behavior versus unobserved runtime outcome distinction | Present | Absent |
| Brief-decompression guidance | Present | Absent |

These observations establish drift, not its cause or the full rendered provenance. They make direct deletion from the installed file insufficient as a durable correction. The rollout decision must reconcile the maintained source, its policy checks, and the effective projection; distinguish personal voice from duplicated portable mechanics; and preserve any useful consumer-specific remainder. The current blanket first-person rule and broad conversation frame can plausibly contribute to the observed PR wording, but this investigation does not prove which instruction caused a particular generated sentence.

## Existing producers and settled decisions

- [Split writing-for-people by concern](https://github.com/nisavid/provingkit/issues/26) is open and unassigned. Its earlier native blockers are closed; charting this map added [Settle medium-aware writing contracts and source placement](https://github.com/nisavid/provingkit/issues/109) as its current native prerequisite, preserving its existing parent and ownership. It already owns the generic/conversation split, conditional `threaded-conversation.md`, removal of the review ask ladder into Mergecraft, corpus changes, and evidence-reference thinning. Its resolution input explicitly carries the source/runtime guard correction. The old 54-rule counts and four-guard target must be reconciled with current bytes; they are not a fresh implementation specification.
- [Add the Mergecraft review-voice reference and projections](https://github.com/nisavid/provingkit/issues/19) is open and unassigned, blocked by the split. The closed [dependency decision](https://github.com/nisavid/provingkit/issues/18#issuecomment-5524048961) settled an external call, intra-plugin projections only, no cross-plugin content lock or embedded fallback, and reduced claims using ambient instructions when the generic writer is unavailable. Its former Tidesmith identifiers require reconciliation with the current Proseweaving identity, not revival as another plugin.
- [Teach writing-for-people to decompress operator briefs](https://github.com/nisavid/provingkit/issues/27) is open and unassigned, blocked by the split. It owns generic brief-to-reader framing and the conversational heads-up shape. Some input has already reached global instructions through the closed global-writing port, but the portable skill does not yet contain that full treatment. Do not duplicate this producer in the new map.

The [disposition ledger](https://github.com/nisavid/provingkit/blob/147e1ddfc969b5119001488ce1556627d3b2449b/release/source-skill-disposition/disposition-ledger.json) retains the external Elements of Style source side by side. Similarity to Proseweaving is not evidence that every installed writing skill should be removed. Retirement requires contribution-level ownership and consumer discovery evidence.

## Decision handoff

The smallest visible source boundary is the existing Proseweaving split plus its references and corpus, Mergecraft's PR body contract and intended generic-writer route, and the dotfiles global-writing source/projection. The writing-contract decision should settle the generic medium rule, conditional conversation guidance, first-person/change-summary distinction, and each consumer's invocation boundary. Its producer handoff should name those source owners and acceptance examples; installation and retirement must consume the reviewed revision rather than independently restating the policy.

Keep historical PR repair, wholesale writing-skill removal, unrelated review machinery, and non-Hatchery installation outside this research resolution. The existing tickets retain their ownership; this note neither claims nor implements them.
