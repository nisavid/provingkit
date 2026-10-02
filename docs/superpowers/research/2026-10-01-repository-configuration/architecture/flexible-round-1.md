# Repository configuration through an editable decision brief

This design gives an agent one reviewable brief for a repository change while preserving the repository's own configuration language, owners, and deliberate choices. The durable interface is an editable document; an agent interprets the supported procedure and prepares owner-specific work from it. Flexibility comes from retaining native representations and scoped reasoning, rather than translating every setting into a universal desired-state model.

This is the independent flexibility lane. It proposes architecture, not accepted policy, executable behavior, or an alpha scope.

## The module and its interface

The **configuration consultation module** owns turning a repository concern into a justified, bounded configuration decision. Its external **seam** is a request and the resulting decision brief. A conversation, maintained document, or harness-discoverable entrypoint can carry that interface. The implementation can acquire evidence and use existing specialist procedures without exposing their mechanics to an ordinary caller.

A request provides:

- A target repository, or an intended repository before creation; the requested outcome and scope.
- Known preferences and deliberate choices. Unspecified preferences remain unspecified.
- Existing applicable policy and configuration ownership when known. The module discovers these when accessible; the caller need not inventory them first.
- The requested operation: explain, recommend, prepare changes, or continue an authorized application. The actual authorization and available controls determine what it can perform.

“Improve CI security” is enough to begin a recommendation. It is insufficient to infer who may change an organization rule or which review model the user must adopt. Read-only discovery should resolve discoverable facts before asking about genuine decisions.

The output brief has a small common spine: target and purpose; observed scope; recommended choices and retained overrides; unresolved decisions; evidence dependencies; and the next authorized work. A consequential choice gets a short addendum containing its rationale, affected behavior, native configuration location and owner, and verification or recovery limits. Addenda use the relevant owner's language. A Terraform-managed setting can reference a Terraform change; a workflow change can show a Git diff; a manual platform setting can have a proposed before/after value. Arbitrary opaque payloads do not become executable merely by appearing in the document.

There is no mandatory list of every setting, relationship taxonomy, numeric confidence score, or exhaustive field-ownership registry. The common spine is a document contract, not a schema for GitHub. Detail earns its place when it changes this decision. Explicit coverage limits prevent an omitted domain from appearing assessed.

### Invariants and ordering

1. Establish purpose, target, supported scope, and current ownership before recommending a managed-field change. Explain independent matters while consequential unknowns remain open.
2. Distinguish observations, documented mechanisms, local policy, preferences, and proposed judgment. An applicable prohibition needs an identified policy; a preference disagreement does not supply one.
3. Preserve supported deliberate choices. Describe the relevant consequence and alternative. Evidenced active harm or a policy conflict goes through the selected stakeholder policy; this architecture does not define that policy.
4. Bind each consequential conclusion to the evidence it used: mechanism source, relevant target observation, and consumed procedure revision where applicable. Changing an input invalidates the conclusions that depend on it, not automatically the entire brief.
5. Present sensible defaults as a concrete set for confirmation when confirmation is needed. Reuse settled authority and choices instead of repeatedly asking.
6. Before application, resolve each changed surface to its existing owner or a specifically selected operation route, refresh application preconditions, and carry forward the user's actual authorization. Application never follows merely from a recommendation being accepted as good advice.

The caller can amend a choice in ordinary prose or edit its addendum. On continuation, the module interprets the amendment against the current brief and regenerates affected proposals. Native payloads and confirmed choices remain individually identifiable; unrelated content is preserved. A later apply request binds the current concrete candidate and its relevant preconditions, not a remembered “yes” to an earlier candidate.

Errors are useful results. An inaccessible setting is **unknown**, not disabled. Conflicting sources produce a qualified recommendation or a narrow unresolved decision. Unsupported content gets research-backed advisory treatment if possible and an explicit limit on application. An ownership conflict stops competing writes but permits an owner-directed proposal. A stale application precondition returns a revised proposal or reconciliation need. A partial application reports confirmed changes, confirmed nonchanges, unknown effects, and which dependent steps cannot proceed. It never reports overall success from the first successful write.

The performance contract is bounded investigation: announce the assessed surface and expand it only for consequential relationships. It promises neither constant time nor an exhaustive audit of an arbitrary repository.

## Concrete use

The following is an illustrative brief fragment for the constructed Python/plugin request, not an assessment of Provingkit:

> **Purpose:** Increase CI security for a public Python/plugin repository with one maintainer and agent assistance. This request authorizes a recommendation.
>
> **Recommend:** First map the existing acceptance claims to their actual jobs and producers. Add or adjust checks for selected uncovered behavior, then choose which results should be mandatory. Investigate CodeQL suitability for the Python and workflow content; absence of default setup does not establish absence of every scanner.
>
> **Keep open:** The desired review independence and eligible reviewer model. Do not promise that an agent approval supplies a qualifying independent review.
>
> **Before proposing required gates:** Establish relevant events, skipped/missing-result behavior, producer identity, and a usable contribution path unless a freeze is intended. Overlapping jobs may already cover a claim.
>
> **Owner handoff:** Put workflow changes through the repository's source owner. Put managed repository settings through their configuration owner. Application and hosted enforcement remain unperformed.

This can become a concrete recommendation once the missing facts are available. It deliberately does not invent a job list or threshold from “Python/plugin.”

For a **new repository**, the caller says, “Create a public project for this team and these contribution paths.” The brief proposes a coherent initial set, explains its assumptions, and leaves organization-owned restrictions with their owner. Repository creation and subsequent settings may have different authorization and recovery properties. A prepared creation specification does not imply that creation ran.

For **defaults**, “Use sensible defaults for our solo-maintainer workflow” produces one confirmable set with material tradeoffs. A workable zero-approval arrangement may be recommended for a particular supported actor model, but it is not installed as a universal solo-maintainer rule. Optional stronger controls remain options unless local policy requires them.

For a **focused concern**, “Reduce exposure from CI dependencies” follows source practices, admission policy, and runtime downloads only far enough to explain the selected claim. Artifact Customs remains the owner for inbound component policy and pin lifecycle. A complete application-security audit is not silently added.

For a **custom override**, “Keep unpinned internal actions permitted; pin this workflow” retains both choices, explains the difference between future admission and current source, and checks applicable policy. If the user also wants every future workflow necessarily pinned, the brief exposes that incompatible outcome rather than silently replacing the selected admission rule.

## What the implementation hides

The module hides evidence acquisition, relevant source retrieval, concern expansion, applicability checks, comparison of plausible options, and preparation of the next owner's input. That is its **depth**: deleting it would make every caller reconstruct those relationships and qualifications.

Knowledge is maintained in small, owner-held explanations and procedures selected for a supported decision, with primary sources attached. The brief records exactly which ones supplied its consequential reasoning. A new supported setting can use an existing native configuration format and add focused guidance and cases without extending a central ontology. Sources outside current supported guidance can inform a limited answer, but do not gain qualified application support by analogy.

This moves maintenance toward the relevant subject owner and keeps **locality** for mechanism corrections. It costs some retrieval and interpretive consistency. The common brief retains dependencies and outcomes; it does not cache a second authoritative copy of every provider's documentation. Freshness is claim-specific: current target state matters before writing, a changed preview matters to eligibility, and a corrected procedure matters to consumers relying on the corrected assumption. No universal expiration period is proposed.

Two owners can contribute incompatible addenda. The module must expose the conflict against the user's goal and governing policy. It does not merge them by numeric priority or whichever instruction was retrieved last. No permanent reconciler, background schedule, automatic conformance score, or universal solver is implied.

## Dependencies and application

Interpretation and comparison are in-process behavior. Repository files, Git inspection, and native configuration drafts are local-substitutable dependencies: fixture repositories and fixture owner files can exercise their ordinary interface. They need no public adapter registration mechanism.

GitHub is a true external dependency. A narrow internal **observation module** is justified for any selected executable observation scope: repeated logic must preserve pagination, permission failures, unsupported reads, source timestamps, and distinctions between local and effective configuration. Its production **adapter** uses the existing GitHub CLI/API route; its replay adapter supplies finite recorded or constructed responses, including failures. Both satisfy the same observation interface for that selected scope. The replay adapter proves handling of supplied responses, not GitHub behavior. The first supported scope determines its concrete operations; this proposal does not invent a generic remote execution interface in advance.

The consultation module consumes these observations and their limits rather than raw success-shaped placeholders. Documentation acquisition is separately recorded; a published claim cannot silently replace a target observation. This pass ran neither adapter.

Application stays owner-specific. Where Safe-Settings, another App, or infrastructure source already owns a field, prepare the change in that source and use its existing deployment procedure. Discovery may reveal only a suspected owner; report that uncertainty before creating a competing writer. Where no owner exists, the selected scope must name a qualified operation-specific actuator or remain preparation-only. A new settings actuator would be a specific ownership decision, not an automatic consequence of choosing this architecture.

Existing Versionkeeping Git/index/ref/push ownership, Mergecraft forge-publication and PR lifecycle ownership, Rolecasting model/delegation ownership, Artifact Customs inbound-component ownership, and current review and release procedures remain intact. Security conclusions requiring specialist review use the applicable security owner. The brief supplies bounded inputs and consumes results; it does not grant those owners authority or bypass their gates.

For a multi-step apply, the addenda state ordering only where effects depend on it. Preserve before-state and recovery information appropriate to the actual operation. Use native concurrency controls where available; otherwise disclose the remaining race and constrain the claim. A lost response means an unknown outcome requiring readback or owner reconciliation. Do not blindly retry, assume cross-system atomicity, or restore old settings over another writer's newer change. A source-plus-settings migration may require recovery of both; rollback itself needs the operation's authority and current-state check.

## Common-case challenge

| Case | Required observable behavior of this design |
| --- | --- |
| Legitimate unconventional choice | Retain it and explain the consequence; no invented prohibition or forced normalization. |
| Intentional freeze versus accidental deadlock | Ask or use established purpose before changing liveness; identical settings can warrant different recommendations. |
| Same check name, changed producer | Mark dependent claims for reconsideration; match producer, revision, event, and promised behavior rather than the display name. |
| Skipped/missing checks or event mismatch | Explain the relevant result semantics and what remains unqualified; do not equate a green label with execution or coverage. |
| Admission permits unpinned actions; source pinned | Report two different facts and propose only the change justified by the selected concern. |
| Scanner enabled without claimed coverage | Keep configuration, completed analysis, useful coverage, and merge decision distinct. |
| Conflicting documentation | Retain both source identities and uncertainty; avoid promising a target capability from the preferred page. |
| Existing configuration writer | Route the native-source proposal to that owner; preserve unmanaged fields and other owners. |
| Procedure correction | Identify affected consumer assumptions from the brief's dependency references and revise those proposals. |
| Partial application/readback unknown | Report per-effect knowledge, hold dependent steps, and reconcile through the owner. |
| Local discovery versus hosted enforcement | Demonstrate separately that a fresh harness can find/invoke the equipment and that a claimed platform behavior occurred. |

These are proposed acceptance outcomes. No examples in this report qualify them.

## Source, qualification, and unresolved choices

Maintain the procedure and brief contract together in an explicitly owned source, with domain explanations close to their existing procedure owners. A focused Skill is a plausible discoverable front end, but the design's interface is the document contract, not Skill packaging. A standalone maintained document with an invocation pointer or a document-producing helper could carry it. An MCP server is not earned merely by supporting flexible input. A new Plugin is justified only if the selected deliverable needs its self-contained identity and components; joining Provingkit's current Slate is a separate decision.

If this grows under Provingkit, canonical source precedes projections. The existing release projector and preview guide demonstrate separate source, artifact, installation, and invocation concerns; they do not authorize extending their current coverage. The implementation map must choose source home, supported harness, deployment route, recovery, and a real consumer. `capturing-agent-procedures` requires that consumer to locate the reviewed revision, load it before dependent work, and return corrections to its owner.

A small qualification plan would:

1. Evaluate the document interface on the shared cases, including nearby requests that should not invoke it. Grade decision usefulness, consequential omissions, false prohibitions, and preservation of deliberate choices.
2. Exercise any selected observation helper against fixture repositories and replay responses. Assert caller-visible unknowns and conclusions, not internal extraction steps.
3. For selected application claims, use only the smallest authorized fixtures needed to distinguish successful readback, unknown outcome, existing-owner coexistence, and the promised hosted behavior. An isolated negative fixture is necessary only where that causal enforcement claim is selected.
4. Review the final maintained revision, deploy the chosen alpha artifact through its owner, and verify fresh-harness discovery and one useful invocation. Preserve deployment and hosted-behavior evidence separately.

A discriminating comparison experiment gives each panel design the same unfamiliar configuration owned by existing infrastructure, then corrects one shared procedure assumption. Measure whether it preserves the native owner and deliberate exception, finds the affected conclusion, asks only necessary questions, and produces a useful amended proposal. Also measure maintainer work to add that setting without expanding a universal schema. A second repetition without supplied relationship hints tests whether this design's reliance on agent reasoning misses interactions that a more structured design catches.

The strongest objection is that flexibility may be paid for with inconsistent reasoning: the document contract can hold every important distinction while the agent still omits one. Its open addenda make novel settings cheap to describe, not automatically safe to support. If controlled comparison shows missed dependencies or unstable owner resolution, narrow the supported scope or add a focused mechanism check. Do not claim success from a well-formed brief.

Possible first-alpha slices include recommendation-only CI review for specified GitHub contexts, concrete proposals through one existing configuration owner, or one narrowly qualified direct operation. Each leaves a different part of the full desired behavior unqualified. Selecting the slice, harm policy, source home, packaging, and target harness remains the human decision.

## Actual exposures and evidence limits

I verified the common-brief SHA-256 `430c73eba6e5352bcca8b3668c3b1771d0cf8e0d257fa95d8be118df4cd430fb`. Repository HEAD was `70879ae2ea94fac8708ab77051d08ded9429fce4`; substantive source baseline was supplied as `02812cdee184023ecc06214e263c308d9131a1b0`. I recomputed research-manifest SHA-256 `351a79780102e27bfd96285fd00b7d102c03ce11999be7da66a6a18b8d57dd5c`; I did not independently repeat the research's source verification.

Actual content reads: `CONTEXT.md`; research `research-synthesis.md`, `method.md`, `verification.md`, `conceptual-follow-up.md`, `github/round-2.md`, and `history/round-2.md`; Versionkeeping, Mergecraft, and Rolecasting READMEs; selected Artifact Customs and Proseweaving README sections; topology top-level keys for Versionkeeping, Mergecraft, and Rolecasting and Versionkeeping's ownership block; `docs/release-artifact-projection.md`; and installation-guide excerpts and search results. One combined read requested the full installation guide but returned truncated output; selected sections were subsequently read. I read `codebase-design`, `DESIGN-IT-TWICE.md`, `DEEPENING.md`, `capturing-agent-procedures` and its producing reference, and installed `checkpointing-and-publishing-git-work` for read-only policy. Root/user instructions and ambient harness metadata, including the injected memory summary, were available; no memory registry or historical transcript was opened or used as substantive evidence.

Initial read-only Git checks found a clean named branch, a non-shallow repository, no upstream configured for this branch, and no merge/rebase operation at the inspected paths. The final status exposed a concurrent untracked research `architecture/` directory; I did not inspect it. Local branch metadata exposed other branch names and subjects; their contents were not opened. No network request established current remote synchronization. No peer architecture artifact, coordinator comparison, live GitHub response, installed payload, or model execution evidence was consumed. This lane made no source, configuration, Git, forge, installation, or tracker mutation and no subdelegation. Its only authored file is this report. All proposed architecture, examples, experiments, and outcomes are hypothetical.
