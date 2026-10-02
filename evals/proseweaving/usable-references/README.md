# Make references usable for their readers

The [writing procedure](../../../plugins/proseweaving/skills/writing-for-people/SKILL.md) gives readers a usable destination when it names work, evidence, or a resource. In a client that supports chat links, it uses the current verified chat title as the clickable label. For chats with the same title, verified project labels may distinguish them when the shared title is clear nearby. An unresolved identity that blocks the answer calls for a narrow clarification question. The [ordinary edit pass](../../../plugins/proseweaving/skills/writing-for-people/references/edit-pass.md) and [finished-draft editor](../../../plugins/proseweaving/skills/editing-finished-drafts/SKILL.md) check title/destination correspondence, missing links, ambiguity, and audience access. This contribution addresses [the reported omission of known chat links](https://github.com/nisavid/provingkit/issues/380).

## Source and composition

The checked source is [`fe388fd5cf1b55edd1a51eb0581bdb895638a633`](https://github.com/nisavid/provingkit/commit/fe388fd5cf1b55edd1a51eb0581bdb895638a633), composed on retained writer/editor source `42a5ca07d47e5b24847bca3e64b8fa531aeba04d` with the meaningful-name contribution from [PR #365](https://github.com/nisavid/provingkit/pull/365) at `a5ebc426579f6d28fa6acadcb84dd8bc4b85c626`. The [source evidence](source-evidence.json) binds the delivered Markdown files, checks, independent reviews, and case correspondence.

The final corpus has 26 writer cases and 12 editor cases. It preserves all fourteen retained writer cases and all six retained editor cases unchanged, adds the six meaningful-name cases by name, and adds six reference scenarios to each route. Only the imported meaningful-name cases receive new numeric coordinates in this composed corpus. Historical requests, outputs, and evidence remain attached to their original coordinates and revisions.

The new scenarios cover a single known chat, several distinct chats, unresolved same-title ambiguity, an unavailable destination, public artifacts with accessible alternatives, and a private source with no public equivalent. The editor cases include a wrong destination, omitted links, an unsupported status claim, and a protected quotation. Client link syntax is a supplied synthetic fixture contract; the portable runtime guidance obtains syntax and identity lookup from the active client's contract.

## Development observations

The [observations](observations.json) retain sixteen prose responses and two description-routing probes. Each prose request ran once in a separate fresh native child: twelve new reference cases and four regressions covering operator-brief framing, an open choice in a finished message, a proposed recovery interface, and protected form. The two routing probes cover four writer queries and twenty-two editor queries.

A distinct native grader received the completed outputs in randomized order with opaque output identifiers, raw inputs, and assertions. The [grading record](grading.json) retains those identifiers alongside meaningful case names. All 48 prose assertions and all 26 routing decisions passed. The executor did not receive expected outputs or grading criteria.

The requested executor configuration was GPT-6 Sol at medium effort; the grader requested GPT-6 Sol at high effort. Each executor first read its supplied packet through a file tool and was instructed to use no tools afterward. Child tool traces were unavailable to the coordinator, so compliance with that instruction and served model identity are not attested. Native harness instructions remained present. All eighteen requests completed without a recorded rejection or truncation. No completed observation was rerun within this set. Request and response digests, nonempty output, unique child identities, and completion were checked in the producing chat. Exact packets and native execution records remain in the private handoff.

These are qualitative development observations. The routing probes assess skill-description selection; they do not establish native discovery or skill loading. One observation per case does not satisfy the retained three-repetition qualification thresholds, demonstrate causal improvement, or qualify all 38 application cases on the final integrated source. The original reported answer is retained as an observed omission, without assigning it to an unverified installed source revision.

## Earlier findings and the settled rule

The [correction record](review-correction.json) preserves two earlier development revisions and their findings. The first set passed its 74 rubric assertions, but final review found that the criteria missed an unconditional title-label requirement in the source. A stricter source and rubric revision then scored 71/74: the writer used project-only labels, and the editor exposed the ambiguity without asking for the missing distinction.

The settled rule permits project-only labels when the shared title is clear nearby. The current source and criteria encode that boundary, and the writer and final edit pass explicitly require the needed clarification. Earlier outputs and grades remain unchanged as historical evidence; the current observations come from eighteen fresh sessions on the revised source.

## Verification and handoff

The Proseweaving validator, all 42 focused contract tests, the source-skill disposition validator, and `git diff --check` pass. Regenerating the content lock twice produces identical bytes. Static analysis of both runtime-only skill packages reports no warnings or failures; a full-source scan counts evaluation support in its deferred-content budget. Independent source and criteria review is clean on this source revision. A composition check confirms that retained cases and fixtures, and imported meaningful-name cases apart from numeric IDs, match their source revisions.

The whole-Kit validator reports `member content identity drift`. This member contribution does not establish a whole-Kit release candidate. The existing integration owner reconciles the combined member identities and reruns affected checks and qualification for the final candidate.

Consumers invoke `proseweaving:writing-for-people` for drafting or editing human-facing prose and `proseweaving:editing-finished-drafts` for a completed draft. The editor already loads the writer and its references; its explicit reference check uses that same rule. Load the reviewed source before dependent evaluation or composition, preserve retained evidence, and bind fresh requests and grades whenever the runtime or its evidence dependencies change. Final integrated qualification, installation, and live acceptance remain with the existing owners under [the Proseweaving map](https://github.com/nisavid/provingkit/issues/12).
