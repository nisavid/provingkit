# An editable repository proposal, built around the caller's task

This design lets a maintainer say what they want to accomplish, receive a concrete repository proposal, and refine it in ordinary language. The agent carries configuration discovery and explanation behind that small interface. The proposal is the work product the caller reviews; it is neither a permanent desired-state declaration nor an instruction to keep reconciling the repository.

This is an initially isolated architecture proposal, not an accepted design, policy, or implemented capability. It consumes research commit `70879ae2ea94fac8708ab77051d08ded9429fce4`; the shared brief and research-manifest digests match their supplied identities. All examples and proposed behavior below are hypothetical. The substantive source baseline is `02812cdee184023ecc06214e263c308d9131a1b0`.

## The caller and the proposed interface

The likely common caller is a maintainer directing a coding agent during ordinary repository work: “Create this project,” “Give this repository sensible defaults,” or “Improve CI security.” This is an inference supported by the requested entry points and the research's scaffold, hardening, and procedure-consumption examples. It is not a measured claim about frequency. A configuration administrator managing hundreds of repositories may need a different interface; that is a useful test of this design's intended reach.

The external seam is the **editable proposal**, expressed in conversation and available as a short document when the task needs continuity. The caller supplies a target or proposed project, an intended outcome, and any preferences or constraints they know. Existing task authorization remains an input even when already established earlier in the conversation. The caller need not fill in owner type, inherited rules, check producers, event eligibility, or capability flags: discovering applicable facts is implementation work.

Three ordinary requests enter the same module:

- **Create:** propose the repository and its initial contribution path, with unresolved owner, visibility, and other consequential choices exposed.
- **Adopt defaults:** recommend a coherent set from the repository's actual purpose and constraints, preserving deliberate choices.
- **Address a concern or review:** explain the relevant current state and propose the smallest useful change set, including related controls when they change the result.

These are recognizable intents, not a required command language. “Keep the release branch frozen, but harden PR checks” is a valid combined request. An unrecognized setting can enter by its native name or documentation; the agent must acknowledge any unsupported interpretation rather than discard it because no predefined entry exists.

A proposal has four reader-facing parts: what I recommend and why; concrete changes and deliberate keeps; consequential assumptions or decisions still needed; and what would establish the promised result. Detailed source and observation records sit behind those claims. Only material uncertainty reaches the top-level conversation. A harmless untouched preference does not earn another warning or approval.

The caller can say “Keep approvals at zero,” “Use the existing Terraform owner,” “Explain this scanner choice,” or “Apply the changes we accepted.” Each edits the same proposal. Acceptance of a recommendation and authority to execute remain distinct, but an existing applicable instruction to execute does not need ritual reconfirmation.

The interface includes these invariants and ordering constraints:

1. Establish purpose, supported scope, applicable policy, existing writers, and available observations before prescribing a change. Ask only about consequential facts that cannot be discovered and actual policy choices.
2. Present the concrete recommendation before any otherwise-required approval. Preserve deliberate exceptions until applicable policy or evidenced active harm requires adjudication; an equipment preference never supplies that policy.
3. Identify selected behavior claims before choosing verification. A repository read, scanner run, and demonstrated merge rejection support different claims.
4. Before execution, refresh affected assumptions and bind the accepted delta to the actual target and owning route. A changed proposal does not inherit acceptance of its prior meaning.
5. Return a scoped result: recommendation complete, decision needed, unsupported portion, application verified to a stated level, or partial/unknown outcome. There is no generic green “secure” badge.

Errors preserve useful work. An inaccessible inherited-rule read leaves effective restrictions unknown; it does not mean absent. A documentation conflict limits the affected recommendation. A missing writer or unsupported setting produces an explicit handoff or partial proposal. The agent can complete independent recommendations without pretending the unresolved item is settled. Broad default assessments cost more discovery than focused requests; the interface promises bounded supported coverage, not an exhaustive audit.

## Four caller examples

**New repository.** “Create a public Python plugin repository for a solo maintainer with agent help.” The agent prepares a concrete setup proposal, infers Python checks from actual planned content, and identifies the intended contributor and release paths. It asks for missing creation identity or policy decisions that matter. It recommends related settings with rationale, rather than importing every Sacrysty or Codiquary choice. Later authorized creation can carry out supported parts through their owners; repository creation itself is a capability requiring an owning route, not silently added to Mergecraft.

**Good defaults.** “Review this repository and adopt sensible defaults.” Discovery finds a deliberate release freeze and an existing configuration manager. The proposal preserves the freeze, recommends independently useful adjustments, and targets the existing manager's source. A newly discovered severe consequence is explained against the repository's purpose; the word “default” does not authorize replacing that purpose.

**Focused concern.** For the brief's public Python/plugin repository with partial checks and no CodeQL default setup, a possible recommendation artifact is:

> I recommend requiring the meaningful Python/plugin validation and test results on the intended PR path, and adding CodeQL analysis for supported Python and workflow content. The exact checks and analysis configuration remain provisional until source and target inspection establishes their fit.
>
> Gate behavior: preserve existing requirements while new or changed producers become available. Require selected test/validation results after their coverage and eligible execution are established. Start new scanning without a new alert gate; recommend its blocking threshold once analysis coverage and your risk policy are known. An enabled scanner alone does not establish that coverage.
>
> Related choices: inspect token permissions and action inputs, then propose concrete least-privilege changes where compatible. Keep agent review advisory under the supplied operating model unless you choose another arrangement; agent assistance alone does not establish an eligible independent approver.
>
> Evidence still needed: effective configuration, selected check coverage, scanner execution where claimed, and hosted rejection only for any enforcement claim selected for qualification. This recommendation authorizes no application.

This is an illustrative provisional recommendation, not a finding that these controls suit the actual repository. With observations available, the proposal must name the selected checks and concrete deltas. It cannot repeatedly sell discovery as the final recommendation.

**Intentional override.** “Keep unpinned actions permitted; our checked-in workflows are pinned.” The agent retains the choice, explains that source practice does not constrain future admission, and considers only applicable policy or evidenced consequences. It can recommend an alternative without inventing a prohibition. If the user names a setting outside supported knowledge, it researches that choice or marks the unresolved semantics; arbitrary customization is accepted as input, not falsely certified as supported application.

## What the implementation hides

The implementation organizes knowledge around performing these tasks: concise decision guidance, authoritative mechanism sources, applicable local policy, and examples that expose consequential mistakes. It retrieves only what the selected claim needs. The source format can remain ordinary maintained documents and small observation helpers; neither a universal setting schema nor a relation engine is necessary to express this proposal.

Behind the proposal, the agent must still connect claims to evidence. For example, a check chosen to reject an invalid release projection needs more than a matching name: its producer, workflow/event path, revision, and actual claimed coverage matter. Those details are included where relevant, not imposed as mandatory fields on every setting. A generic “update repository configuration” wrapper that merely hands all this reasoning back to callers fails the depth test.

**Depth** comes from absorbing discovery, interaction reasoning, and explanation into one usable proposal. **Locality** comes from correcting mechanism guidance and its discriminating examples together in one maintained source. Existing domain procedures remain referenced owners, not copied fragments. Deleting this module should make each caller reconstruct those tasks; deleting a presentation-only wrapper should not.

The proposal record retains consumed guidance/procedure revisions and the supporting observations for material claims. Target drift invalidates affected application assumptions; corrected procedure semantics invalidate affected recommendations and consumer assumptions; contradictory platform documentation limits mechanism confidence. These are targeted dependencies. Unrelated guidance changes do not automatically require repeating every test.

## Dependencies and application

Repository files, policy documents, Git state, and local processes are **local-substitutable** dependencies. Tests can use temporary repositories and files through the ordinary filesystem/process route; no filesystem abstraction needs to become caller-facing. Reasoning over a supplied snapshot is in-process work.

GitHub is **true external**. A narrow internal observation seam is justified by two real needs: live acquisition and reproducible incomplete/error cases. One adapter could use the existing authenticated `gh`/GitHub API route; a replay adapter would return retained responses, pagination, permission failures, missing surfaces, and changed observations. It must preserve raw evidence and distinguish unsupported, inaccessible, and absent results. Replay establishes reasoning on supplied facts, never live platform behavior. This report specifies no API syntax and makes no new live requests.

Application is a later stage of the same task, not a continuing reconciler. The accepted proposal hands fully specified work to existing owners: Versionkeeping for Git publication, Mergecraft for applicable forge/PR operations, Artifact Customs for inbound component adoption or pinning policy, review equipment for review, and Rolecasting for delegation/model selection. Repository-setting operations not owned there need an explicitly selected narrow actuator or the repository's existing manager. This design neither invents permission for a generic writer nor transfers those owners.

When application is in scope, the procedure orders source preparation, producer availability, and gate changes according to the specific migration. It records field ownership and before-state, stops affected writes on drift, and verifies what can be read back. A partial result names confirmed effects, unconfirmed effects, and untouched work. It must not repeat an uncertain non-idempotent action blindly or describe best-effort compensation as an atomic rollback. Recovery may require source and guidance restoration as well as settings; its limits belong in the concrete proposal before execution. Adjacent owners retain their own authorization and recovery rules.

## Common cases that can disprove the design

| Case | Required behavior at the proposal interface |
| --- | --- |
| Legitimate unconventional choice | Retain it; separate recommendation from policy and unsupported execution. |
| Freeze versus accidental deadlock | Use purpose and reviewer eligibility; do not mechanically restore liveness. |
| Same check name, different producer | Revisit the evidence claim and gate binding; display-name equality is insufficient. |
| Skipped/missing checks or event mismatch | Explain what ran and what the required result promises; do not equate an accepted conclusion with exercised coverage. |
| Pins in source, permissive Actions admission | Explain both facts without claiming present source is unpinned. |
| Enabled scanner without coverage | Preserve configuration evidence and identify the missing analysis claim. |
| Conflicting documentation | Retain competing claims and target uncertainty; do not pick the convenient source silently. |
| Existing configuration writer | Propose changes through its maintained source or an agreed ownership change. |
| Corrected consumed procedure | Identify affected assumptions, revise the proposal, and renew dependent verification. |
| Partial application/readback unknown | Report confirmed and unknown effects separately; avoid blind replay or invented restoration. |
| Local discovery versus hosted enforcement | Verify each selected claim independently; successful installation proves neither invocation nor merge rejection. |

## Source home, integration, and qualification

The proposed reusable source owns the task procedure and its maintained guidance, while repository-specific policy and accepted choices stay with the repository or active task. A repo-carried procedure is a plausible first source home while applicability is established. A standalone Skill with references/helper resources, an independently releasable Plugin, or equipment consumed by an existing repository-creation workflow can expose this same interface. A separate interactive application would be justified only by evidence that editing or comparing proposals needs more than the harness conversation. Packaging, names, target harnesses, and eventual Agentworks promotion remain operator choices; this proposal does not add a member to the current Slate.

Provingkit's current source trees and published installable projections are distinct. If this equipment later uses that release machinery, build-time projection, receipt preservation, installed payload checks, and fresh discovery must follow the owning route. It cannot make installation run the projector or call a single-member alpha a whole-Kit Release.

Qualification should begin with the caller interface:

1. Give competing designs the same frozen facts for the common cases above, including held-out combinations. Compare omitted consequential facts, false prohibitions, useful concrete choices, needless questions, explanation accuracy, and caller effort. Do not reward shorter answers that hide missing reasoning.
2. Correct one procedure assumption, change a producer while keeping its check name, and introduce an unfamiliar setting. Measure whether each design updates only affected claims, preserves the override, and reaches a concrete revised proposal. Count maintainer effort to correct knowledge and examples, not just caller turns.
3. For selected executable scope, exercise local temporary repositories and live/replay observation adapters. Then run the smallest separately authorized hosted cases needed for claimed application or enforcement, isolating unrelated gates. Test ordinary-language discovery and non-invocation separately in the chosen installed harness.

The strongest objection is that a polished conversational proposal can conceal nondeterministic retrieval and incomplete interaction reasoning. Maintainers could accumulate sprawling guidance while callers receive persuasive but inconsistent answers. If identical facts yield materially different gates, or the update experiment leaves stale advice, the design fails despite an attractive interface. Strong human explanation cannot substitute for reliable behavior. A second tradeoff is that ongoing fleet reconciliation and exhaustive arbitrary-setting management are awkward fits; adding them would change the module's claim and likely its seam.

Possible first-alpha increments include recommendation-only for one repository context; concrete source/configuration proposals with manual execution; or a narrowly supported apply route with readback. Each could exercise creation, defaults, or a focused concern. The operator must select capability and context before implementation and qualification costs are fixed. Procedure capture, reviewed source discovery, targeted deployment, and actual consumer invocation belong in the implementation map; this report completes none of them.

## Actual exposure and limits

I read the common brief; repository `AGENTS.md` and `CONTEXT.md`; the research synthesis, method, conceptual follow-up, GitHub round 2, history round 2, and verification; and the research-manifest bytes for their digest. Research citations and observations remain attributed to that packet; I did not independently repeat their primary-source work. Source ownership checks read the six current Plugin READMEs or focused portions, `docs/release-artifact-projection.md`, and focused installation/verification portions of `docs/preview/install-and-update.md`. No topology implementation was needed for this proposal.

Standing-skill exposures were `codebase-design`, `DESIGN-IT-TWICE.md`, `DEEPENING.md`, `improve-codebase-architecture`, `capturing-agent-procedures` and its producing reference, `grilling`, and installed Versionkeeping's `checkpointing-and-publishing-git-work`. The task's bounded design delegation overrides the broader skills' implementation, interview, HTML-output, and subdelegation steps. Consequential decisions are returned for the coordinator's operator round.

Ambient harness instructions and memory summary were visible. A narrow memory-registry search returned no relevant hits; no memory-derived finding is used. Read-only Git commands exposed repository state and branch/worktree metadata, including unrelated branch names; no other branch content was read. The assigned branch was clean at the research commit, with no active Git-operation markers and no configured upstream. No remote freshness or unpublished-state claim follows from those local observations.

I read no peer architecture report or later coordinator comparison, used no subagents, made no provider request, ran no behavioral fixture, and changed only this report. Isolation is a declared read discipline, not product-enforced secrecy. The initial report is to be frozen before peer exchange.
