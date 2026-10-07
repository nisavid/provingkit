# Make publication coverage inspectable before adding another judgment

I recommend developing one narrow candidate: an **on-demand comparison between the outgoing documentation changes and their existing review and verification records**. Its consumer is the agent preparing publication, with an optional source-linked view for Ivan. Its decision is concrete: which publication obligations already have applicable evidence, and which differences still need explanation?

Start with deterministic organization and ordinary interpretation. I would not assign Jev to this candidate now. The serious semantic rival is checking selected research claims against their cited passages before final review. That rival has a more plausible Jev subtask, but a less clearly economical context producer.

This recommendation advances beyond the earlier proposal to observe an entire publication. It names an inspectable output, uses an existing verification-record shape, identifies a real false-alarm trap, and gives the coordinator an inexpensive way to reject the idea before commissioning another native observation.

## What the evidence supports

The earlier staged and publication reports already proposed identity checks and obligation reconciliation. Their limitations remain: prescribed review does not establish removable work, and successful publication does not establish an assessment’s contribution. The later observation retained artifacts but lacked current chat events. Its index-tree request caused the terminal interruption; that interruption cannot support a native-benefit claim. [Workflow synthesis][workflow]; [publication observation][observation].

The commit-message observation is also a useful negative constraint. It produced an accurate message and no separately observed message-review operation that a replacement could remove. I would therefore leave message authoring with the ordinary agent. Reconstructing commit scope merely to ask Jev whether that reconstruction is accurate has no demonstrated advantage here. [Commit observation][commit].

There is, however, a concrete publication comparison already latent in the public artifacts:

- The retained publication involved nine outgoing files.
- Its verification record lists seven reviewed content files and five review scopes.
- The publication additionally carries the review and verification records themselves.

The earlier push report explicitly distinguishes those sets. A naïve “outgoing files minus reviewed files” alarm would identify two differences without establishing two missing reviews. Conversely, treating one clean review as coverage for every outgoing object would overstate it. [Push report][push]; [verification record][verification].

This is a useful design case even though the source does not show that anybody struggled with it.

## Strongest candidate: show the unresolved publication differences

**Consumer and ordinary workflow.** The publishing agent prepares task-owned changes, completes applicable checks and reviews, commits them, prepares the publication operation, and verifies its result. Ivan may inspect the resulting evidence. The proposed aid belongs immediately before ordinary publication review, when the intended outgoing range is known. It should be requested on demand or incorporated into an existing review view, rather than interrupting every commit or push.

For the initial scope, use documentation/research publication through one existing-branch update. Exclude plugin qualification, release operations, multiple refs, deletions, and security judgments. Broader range forms need their own handling; unsupported forms must remain explicitly unsupported.

**Proposed output.** Present the actual outgoing paths alongside the existing records, exposing:

1. Content whose recorded digest matches, with the review’s stated scope and dependency limitations.
2. Content or recorded dependencies that changed after review.
3. Outgoing content not named by the supplied record.
4. Review and verification records carried by the publication, shown separately without assuming they require self-review or are exempt from required review.
5. Required checks whose supplied evidence is absent, stale, failed, or explicitly inapplicable.

The output should say “not covered by this supplied record,” rather than “unreviewed,” unless the available evidence establishes the stronger claim. Digest equality identifies bytes; it does not establish that all selected review focuses passed or that an omitted dependency remained unchanged.

**Producer and available inputs.** Git supplies committed content and the proposed source/target identities. Existing verification records supply reviewed paths, digests, scopes, and links. The active agent supplies applicable task requirements and any interpretation that cannot be obtained mechanically. The source of each interpretation remains visible.

The present Versionkeeping workflow already binds immutable publication inputs and requires final verification. Its transport bypasses ambient hooks, making an ordinary pre-push hook an unsuitable assumed delivery route for this workflow. The candidate would consume inputs already produced during authorized preparation; it would not run the publication planner merely to collect research data or alter its gates. [Checkpoint workflow][checkpoint]; [publication execution][execution].

A small read-only adapter could compare these existing artifacts and render links. That is a proposed implementation, not installed equipment. Do not build a new requirements ledger or infer a complete dependency graph from Markdown citations.

**Expected benefit, currently unmeasured.** The view could reduce repeated searches for review coverage, make a newly added outgoing commit visible, and help Ivan inspect a specific unresolved difference. It does not replace required review. The proposed work removed is reconstruction of coverage, only if that work actually occurs.

### Illustrative decision

Consider the retained nine-file publication. A useful view would show the seven reviewed content files with their recorded identities and scopes, then separately identify the review and verification records.

The agent can then answer a narrow question: “Does the existing publication procedure already account for these two supporting records?” The view must not demand two new reviews merely because they are absent from their own content manifest.

Now suppose an additional documentation commit enters the outgoing range after that review. The view would expose its files as outside the supplied record. Ordinary policy interpretation decides what review or verification they require. If the extra commit merely contains an already-completed obligation with applicable evidence, the view should link that evidence instead of repeating a warning.

These are authored contrasts. Only the original nine-versus-seven distinction is a retained source finding.

### Why this candidate could lose

Partial staging defeats a view built from working-tree bytes. Before commit, it must use staged content; after commit, it must use the immutable committed content. It must never let a full-file review silently cover a different staged subset.

Changed claims, dependencies, requirements, or outgoing ranges can invalidate the apparent coverage even when some path hashes still match. Missing dependency declarations limit the view’s conclusion; they do not justify claiming freshness.

Already-completed obligations are equally important. If the ordinary publication workflow already gives the agent a compact, trustworthy account of them, this extra view adds maintenance and reading. Omission should win. If generating the view requires the agent to perform the entire reconciliation first and then encode it again, the candidate also loses.

## Serious rival: check cited claims while authoring research

The rival consumer is the research author deciding whether a changed sentence faithfully represents its cited source. Its output would identify a supplied claim–passage pair as supported, contradicted, unaddressed, or insufficiently contextualized. Delivery should occur during authoring or focused review, when correction is cheap, rather than after message writing.

There is a concrete public implementation precedent. TypeSafe’s citation-checking cookbook first performs deterministic quote matching, then classifies the relationship between a claim and a supplied source section. Its eight examples contain four deliberately edited failures and use cached Jev results. This supports feasibility of that decomposition; it establishes neither local reliability nor savings. Its exact-match stage can also misclassify lightly reworded quotations. I would retain a neutral “quote not matched” result rather than import its stronger label. [TypeSafe citation cookbook][citations].

A relevant authored example is:

> Claim: “The publication observation established successful publication and reduced verification effort.”

The retained result supports neither assertion within the observation. It places successful publication outside the observation and leaves effort unmeasured. An accurate alternative would preserve those limits. This pair illustrates an intelligible semantic decision, not an observed mistake by the ordinary author. [Publication observation][observation].

**Why this rival might win.** A publication view cannot detect a false inference inside correctly reviewed and correctly hashed text. Claim checking targets that semantic gap directly. It may be more useful when authors already prepare bounded citations and reviewers spend substantial time reopening sources.

**Why I rank it second.** Selecting material claims, retrieving sufficient context, preserving qualifications, and handling multi-source arguments are substantial producer work. Jev returns typed decisions, not rewritten claims or explanations. The author still owns correction and the required reviewer still reviews the final revision. A score may therefore add another check without removing anything. [TypeSafe coding-agent guidance][jev].

Ordinary reading of adjacent claim and source, deterministic links and quote checks, and omission remain serious competitors. No threshold from the cookbook should become a local acceptance threshold.

## Minimal comparison that could defeat the recommendation

The next step should be a **worked comparison design**, not another broad collection contract.

Using the existing public publication and verification artifacts, have the coordinator sketch the ordinary evidence presentation and the proposed difference view. Determine whether the proposed view answers a question the ordinary presentation leaves laborious or unclear. Test four authored variations conceptually: an additional outgoing document, changed reviewed bytes, changed evidence dependencies, and the original supporting-record difference.

If the view cannot distinguish those cases without extensive new semantic annotation, stop developing it. That defeats the claimed cheap producer.

If it remains promising and Ivan selects the scope, a later accepted comparison should evaluate ordinary preparation, deterministic presentation, and omission using equivalent decisions and task-quality requirements. Measure preparation and consumer effort together. Avoid showing the same consumer the same case twice and interpreting learned answers as assistance savings.

For the citation rival, the corresponding first discriminator is whether normal authoring already provides sufficient claim–passage pairs. If constructing those pairs performs most of the review, do not proceed to a model comparison. If pairs exist at low marginal cost and the semantic task remains useful, compare ordinary reading, deterministic assistance alone, and Jev on identical available context. Required final reviews remain unchanged.

## Costs and the coordinator’s next decision

The producer owns retrieval, identity comparison, requirement selection, rendering, refresh, and failures. The publishing agent owns interpretation and corrections. Ivan’s checking time and interruptions are a separate outcome. Maintainers own adapters, record-format changes, policy drift, and invalidation behavior. A semantic arm additionally owns claim selection, passage retrieval, every request, retries, uncertain-result handling, and downstream rechecking.

Count shared preparation once when completion or continuity already produces matching records. Retain standalone cost and each consumer’s marginal cost. Separate research expenditure from recurring operation. Model capacity, operator effort, latency, and money remain distinct; their values are currently unknown.

The coordinator should decide the following at the cross-lane join:

| Finding to establish | Consequence |
| --- | --- |
| Existing records can produce a useful coverage view with little extra interpretation | Present this candidate for scope selection. |
| Ordinary publication already supplies an equally usable view | Prefer omission; do not add a classifier. |
| Coverage requires a new comprehensive semantic ledger | Defer this implementation rather than treating that producer as free. |
| Claim–passage pairs already exist and source checking is a meaningful burden | Elevate the citation rival for scope selection. |
| Neither candidate changes a consumer decision or reduces plausible work | Retain ordinary authoring and publication; assign neither a new role. |

The required capture is this proposal and its eventual decision. If selected and validated, its maintained source and invocation point should be chosen through `capturing-agent-procedures`; no unsettled convention belongs in installed instructions now.

## Source identities and limits

I read all fifteen shared public inputs and verified their declared SHA-256 digests before and after inspection. The repository revision was `ca2c510c304cb7fd3216a1f2b0ac02645dceea12`. I also inspected the published acceptance record, checkpoint procedure, publication reference, verification record, and commit observation. The consumed comparison-contract digest was `9f876cd27c4bd6fe82d56feabc6e31e05d029d7cac18f9651194218e2e1aa981`.

The TypeSafe pages were read on October 7, 2026. They are vendor documentation, not independent efficacy evidence. I made no Jev requests, experiments, private-history reads, sibling-report reads, or writes. These are independent research recommendations; benefit, reliability, and population efficacy remain unqualified.

[workflow]: https://github.com/nisavid/provingkit/blob/ca2c510c304cb7fd3216a1f2b0ac02645dceea12/docs/superpowers/research/evidence/jev-axi-workflow-opportunities-2026-10-05/README.md
[observation]: https://github.com/nisavid/provingkit/blob/ca2c510c304cb7fd3216a1f2b0ac02645dceea12/docs/superpowers/research/evidence/jev-axi-publication-observation-2026-10-05/results.md
[commit]: https://github.com/nisavid/provingkit/blob/ca2c510c304cb7fd3216a1f2b0ac02645dceea12/docs/superpowers/research/evidence/jev-axi-commit-observation-fourth-attempt-2026-10-04/README.md
[push]: https://github.com/nisavid/provingkit/blob/ca2c510c304cb7fd3216a1f2b0ac02645dceea12/docs/superpowers/research/evidence/jev-axi-workflow-opportunities-2026-10-05/push-workflow.md
[verification]: https://github.com/nisavid/provingkit/blob/ca2c510c304cb7fd3216a1f2b0ac02645dceea12/docs/superpowers/research/evidence/jev-axi-consumer-opportunities-2026-10-04/verification.json
[checkpoint]: https://github.com/nisavid/provingkit/blob/ca2c510c304cb7fd3216a1f2b0ac02645dceea12/plugins/versionkeeping/skills/checkpointing-and-publishing-git-work/SKILL.md
[execution]: https://github.com/nisavid/provingkit/blob/ca2c510c304cb7fd3216a1f2b0ac02645dceea12/plugins/versionkeeping/skills/checkpointing-and-publishing-git-work/references/publication-execution.md
[citations]: https://docs.typesafe.ai/cookbooks/citation_check.md
[jev]: https://docs.typesafe.ai/introduction/coding-agents.md