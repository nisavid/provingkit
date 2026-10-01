# Repository-configuration equipment: independent conceptual-design hypotheses

This report offers three testable ways to help an agent choose, explain, and qualify repository configuration while keeping its starting instructions short. It does not select an architecture, settle what counts as harmful, or authorize configuration changes. My initial hypothesis is that a concern-indexed casebook will be sufficient for the first bounded use, but a sparse relationship model or behavior-first model may prove necessary where important interactions cannot be retrieved reliably.

## Status, evidence, and exposure

**Revision:** round 1, frozen independent conceptual-design lane.

**Authorized outcome:** one research report comparing proposals against the supplied problem. The acceptance evidence for this report is an explicit comparison, constructed counterexamples, falsifiable claims, distinguishing experiments, and a complete account of its inputs and limits. Runtime qualification, architecture acceptance, implementation, publication, and adoption are outside this increment. [P1]

**Direct inputs and policy sources:**

- **[P1] Frozen problem supplied in this lane's task message.** The desired equipment is reusable and adaptable, with complex helpful behavior and simple core instructions. It should catalog settings, interactions, effects on repository behavior, and rationale; recommend related settings and defaults; permit a presumed recommended configuration with confirmation for repository creation or default application; preserve arbitrary user choices except actively harmful or established-policy-incompatible ones; and investigate extensively hardened CI fitted to a project's stack, layout, and content and connected to strict protection gates. Research precedes codification, and settings, ownership, packaging, implementation, and adoption remain decisions.
- **[P2] User-supplied governing instructions for this repository.** Relevant sections are Development Work, Writing, Interaction, Delegation, and General Policy: treat plans as hypotheses; define the increment and its evidence; keep unsettled conventions out of durable instructions; distinguish observed outcomes from constructed conditions; use existing domain language; preserve stakeholder decisions; and capture proposed reusable procedures without prematurely installing them.
- **[P3] Repository `AGENTS.md`, read directly.** Project Context requires canonical language from `CONTEXT.md`. Operating Policy favors verified repository facts, reserves project initiatives to the user, and calls for escalation when stakeholder policy is unknown. No tracker, plugin, or configuration source referenced by that file was opened.
- **[P4] Repository `CONTEXT.md`, read directly.** Relevant language is Agent Equipment, Skill, Plugin, Client/Harness, Ambient Runtime Capability, Semantic Writer, Actuator, Candidate, Receipt, Projection, and Refresh Contract. The external specification linked there was not opened. Its glossary is used as local policy; no independent claim about that specification is made.

**Method guidance read:** `research/SKILL.md`, `domain-modeling/SKILL.md`, and `capturing-agent-procedures/SKILL.md` from the installed generic skill collection. I am the delegated background researcher required by `research`; there was no further delegation. Domain-modeling guidance informed terminology and constructed counterexamples. Procedure-capture guidance informed the proposal and consumer interfaces below. Neither resulted in a durable instruction edit. The task's explicit output boundary takes precedence over those skills' normal repository-note or glossary-edit locations.

**Exposure inventory:** the lane received its own frozen task and the harness's governing instructions, environment metadata, and ambient memory summary. I did not query persistent memory or use memory-derived project history as evidence. The only repository contents read were root `AGENTS.md` and `CONTEXT.md`; discovery listed only root instruction/context filenames. No current or previous repository configuration sources, GitHub documentation, solution survey, named-project history, issue findings, parent research transcript, peer artifact, or later-round packet was read. No Git inspection, tracker action, installed-equipment change, network access, or external message was performed. The only authored artifact is this file.

**Limits:** all architecture, data fields, interfaces, algorithms, and experiments below are **proposals**. Every worked case is **constructed**, including the CI examples. They establish questions and potential failure modes, not facts about GitHub, any other forge, or any existing implementation. No proposal has measured retrieval quality, evaluated agent behavior, demonstrated a platform capability, or acquired an owner. Platform verification and external evidence are deliberately deferred. [P1–P4]

## What the equipment would need to distinguish

The central problem is not merely finding a setting. The agent needs to connect a user's concern to a relevant choice, explain the choice's consequences, discover interactions that could defeat the concern, and distinguish an attractive plan from observed behavior. That decomposition is an interpretation of the supplied goal, offered for testing. [P1]

I propose the following working terms. These are local research vocabulary, not additions to `CONTEXT.md`:

| Term | Proposed meaning | Distinction it preserves |
| --- | --- | --- |
| Concern | An outcome a person values, such as receiving useful feedback before accepting a change. | A concern can have several possible implementations. |
| Setting | A configurable choice within a named scope and platform context. | Its name or accepted value does not itself establish its effect. |
| Observation | A dated reading of repository content, configured state, or executed behavior. | Unknown, inaccessible, absent, and observed-disabled remain different. |
| Policy constraint | An applicable requirement backed by an identified authority. | It is separate from a recommendation and from the agent's preference. |
| Recommendation | A proposed choice, its reasons, alternatives, relevant conditions, and expected consequences. | Disagreeing with a recommendation need not violate a constraint. |
| Interaction | A conditional relationship among choices, observations, and outcomes. | Some interactions affect usefulness or cost without being hard dependencies. |
| Configuration plan | The bound set of proposed changes and qualifications for one repository. | It is separate from a reusable catalog and from permission to apply it. |
| Behavior claim | An outcome asserted under explicit conditions, with a way to challenge it. | Reading a configuration value is insufficient evidence for the whole claim. |
| Recommended set | A coherent, explainable starting selection that the user can modify. | It is not a Plugin, Kit release, or Base Loadout by implication. |

The last distinction matters because the problem uses “package” conversationally, while local policy gives packaging terms specific meanings. I use **recommended set** for defaults and leave the eventual Agent Equipment form open. A Skill, Plugin, or another arrangement remains a later decision. [P1, P4]

The model should also avoid making a setting, a check, and a gate synonyms. In a constructed CI case, a check is intended to establish some behavior; an execution mechanism runs it; a gate consumes a result when deciding whether a change can proceed. The proposal would represent their connection explicitly enough to challenge it, without assuming any forge's implementation.

## Three materially different design proposals

### A. Concern-indexed casebook

**Representation and retrieval.** Maintain short human-readable entries grouped by user concern and recognizable repository circumstances. Each entry contains applicability questions, candidate settings, rationale, expected consequences, related entries, known failure cases, and evidence pointers. A small concern index and explicit cross-links guide an agent to the relevant entries. The agent performs the final reasoning in the current task.

**Constructed example.** An entry for “Only accept changes after applicable checks succeed” would lead to questions about which content needs checks, which changes cause them to run, how their results are identified, and how a gate interprets missing or unsuccessful results. A related entry could address the concern that a documentation-only repository should not acquire irrelevant application checks.

**Strengths proposed for testing.** It can retain nuanced reasoning and exceptions without inventing a general constraint language. Entries can be reviewed by reading a few local examples. The core Skill could remain a short dispatch and completion procedure. It is likely the cheapest paper prototype and the easiest place to preserve unresolved questions visibly.

**Failures and costs.** An agent can fail to follow a critical cross-link, overlook a conditional interaction, or explain an inherited default as though it were policy. Retrieval may favor the wording of a familiar case rather than the actual conditions. Review and maintenance costs grow when several entries repeat the same relationship. A casebook also provides no automatic contradiction proof.

**What would falsify its sufficiency.** If, given all necessary entries, independent runs repeatedly omit an essential interaction in a held-out case, merely improving prose may not be enough. The missing relation may require explicit structured traversal or a different unit of retrieval. The smallest useful evidence is an independently adjudicated failure on a constructed variant that differs from an exemplar in one consequential condition.

### B. Sparse relationship model with explanatory records

**Representation and retrieval.** Represent concerns, choices, applicable conditions, policy constraints, and behavior claims as named records. Store explicit conditional relations only where they change a decision. Starting from a concern or proposed setting, retrieve the affected records and enough adjacent relations to explain dependencies, alternatives, and conflicts. Keep nuanced rationale in attached prose. Storage could be ordinary files; this proposal does not require a graph database or solver.

Relations would have distinct meanings: a necessary prerequisite, an incompatible choice, an alternative route to the same concern, a recommendation, or a possible consequence. Direction, conditions, and evidence belong to the relation. “Recommended alongside” must not become “required by” merely because both are links.

**Constructed example.** A gate's desired behavior would be related to the identity of its intended check, the circumstances under which that check produces a result, and the decision taken when a result is missing. Changing a check's identity would retrieve the consuming gate for reconsideration. It would not prove that a real platform implements any of those semantics.

**Strengths proposed for testing.** The same interaction can serve several concerns without duplicated prose. An explanation can show why a setting was included, which condition triggered it, and which supplied policy creates an actual constraint. Structured retrieval could expose forgotten dependents and distinguish a conflict from a preference disagreement.

**Failures and costs.** A clean model may omit the most important real relation. A formal-looking answer may create false confidence when applicability facts are stale or unknown. Relation authoring, conditional scope, cycles, and competing evidence can turn the knowledge base into a programming language. Solving a modeled configuration does not establish that its real behavior is correct.

**Bound on complexity.** Start with named records and a few relation types justified by concrete decisions. Do not enumerate every pair of settings or encode every platform nuance. Unknown edges remain a research limit. If a proposed machine rule cannot be explained with a concrete case, leave it as an open question or prose until evidence warrants structure.

**What would falsify its value.** If structured relations add substantial authoring effort yet do not improve detection of consequential interactions or explanation quality over A on the same cases, they have not earned their cost. The smallest distinguishing evidence is a linked-change case where A misses a dependent and B retrieves it correctly, with both using the same underlying knowledge.

### C. Behavior-first scenarios with configuration strategies

**Representation and retrieval.** Index the catalog by observable outcomes and counterexamples. Each scenario specifies initial circumstances, an event, the expected result, failure observations, and alternative configuration strategies that might realize it. Settings remain cataloged, but the primary entry point is “What should happen when this change is proposed?” rather than a setting family. The agent retrieves strategies by matching concerns and repository circumstances, then explains and qualifies a selected strategy.

**Constructed example.** “A change affecting executable code with a failing required check cannot proceed” is paired with cases for an omitted result, a skipped execution, unrelated content, and a renamed check. A strategy might use different settings on different platforms, while the stated behavior claim remains comparable.

**Strengths proposed for testing.** The catalog leads with consequences users can recognize. It may reveal gaps that a configuration readback overlooks. Different setting combinations can be compared against the same intended behavior, preserving room for arbitrary user choices that meet the concern differently.

**Failures and costs.** A finite scenario set cannot establish all important behavior. This model needs an agreed expected result for each case; unsettled stakeholder policy cannot be replaced with a test author's opinion. Executable scenarios may require costly, unavailable, or intrusive facilities. A setting-level question may become harder to answer unless a reverse index exists. Strategies can duplicate configuration knowledge and drift apart.

**Bound on complexity.** Scenarios may begin as reviewable paper examples, with clearly unobserved outcomes. Automate only the behavior claims whose test cost and authority are understood. Use scenarios that separate competing strategies; do not write one superficial test for every setting.

**What would falsify its primacy.** If ordinary setting questions require extensive reconstruction, or relevant claims cannot be safely observed at reasonable cost, scenarios may serve better as qualification evidence than as the catalog's main representation. The smallest distinguishing evidence is one case where readback is identical but observed outcomes differ; C earns value only if its scenario exposes the meaningful difference.

### Comparison and provisional direction

| Decision | A: casebook | B: relationships | C: behavior first |
| --- | --- | --- | --- |
| Primary retrieval unit | Concern and circumstance | Affected entities and conditional relations | Outcome and counterexample |
| Main reasoning burden | Current agent interpreting prose | Catalog author encoding relations, then agent interpreting results | Scenario author defining outcomes, then agent choosing strategies |
| Natural explanation | Narrative rationale and comparable cases | Why each relation or condition applies | Which behavior a choice is expected to achieve |
| Distinctive blind spot | Relevant entry never retrieved | Important relation never modeled | Important behavior never exercised |
| Earliest useful prototype | A few entries and a concern index | Same knowledge as sparse named relations | Same concerns as reviewable scenarios |
| Likely ongoing cost to measure | Retrieval failures and repeated prose | Relation maintenance and semantic complexity | Scenario maintenance and observation cost |

**Provisional recommendation:** first compare A and B on a small shared set of cases, and use C to challenge both. This is an experiment design, not a decision to ship a hybrid. If A reliably retrieves the needed interactions, prefer its smaller maintenance burden. If B prevents meaningful omissions, add only the structure that caused that improvement. If C substantially changes which strategies are considered acceptable, reconsider whether behaviors should become the primary index. “Simple core” should be assessed together with the knowledge-maintenance and qualification work it creates, not by counting Skill lines alone. [P1]

## Questions that every proposal must handle

### Rationale, source qualification, and freshness

The proposed catalog should distinguish three kinds of rationale:

1. **A platform mechanism claim:** what a setting is said to do, in which platform/version/account context, and according to which source. No such claim is established in this report.
2. **A policy reason:** whose applicable requirement calls for the behavior. A sourced platform fact does not create policy.
3. **A recommendation argument:** why a choice fits the current concern, with benefits, costs, alternatives, and uncertainty. It remains open to user disagreement where no applicable constraint forbids the alternative.

For freshness, three options deserve comparison. A curated versioned corpus offers stable reviewable inputs but may lag platform changes. Just-in-time source checks offer current evidence but increase latency and make results harder to reproduce unless captured. A mixed approach retains a reviewed corpus and refreshes only material uncertain claims at the point of decision; it costs less than universal rereading only if relevance selection is dependable. These are proposed tradeoffs, not measured outcomes.

A source record could identify the claim, source locator and revision, applicable platform context, verification date, and known uncertainty. Dates alone do not prove validity. Qualification evidence should state which catalog revision, repository observations, policies, and platform behavior it depends on. A change to one dependency should invalidate the affected claims or prompt reevaluation; it should not silently preserve an old pass. This extends the repository's candidate/evidence discipline as a proposal for this domain. [P2, P4]

### Dependencies, conflicts, and incomplete knowledge

The agent should first distinguish an impossible combination, an unmet prerequisite, a tradeoff, an unsupported circumstance, and missing information. Treating all of them as “conflicts” would obscure what the user can decide.

For a constructed dependency cycle, setting A may be useful only with B while B may be useful only with A. That may describe a coherent jointly selected set rather than an error. A separate constructed case in which A requires B and prohibits B would be unsatisfied under its stated conditions. The model should show the smallest conflicting set and the relevant assumptions; it should not invent an ordering to make the contradiction disappear.

Alternatives should be explored from the concern outward. If a user declines one recommended check mechanism, another mechanism might meet the same behavior claim. Whether that alternative is available or acceptable requires actual evidence and policy. Unknown platform behavior should remain unknown, not be treated as disabled, harmless, or impossible.

### User choice, confirmation, and harm

The frozen problem permits arbitrary user choices except actively harmful or established-policy-incompatible configurations, while expressly leaving “harmful” unsettled. Therefore this report proposes a distinction among **recommended**, **allowed but discouraged**, **incompatible with an identified applicable policy**, and **unresolved potential harm**. The last category is a question for stakeholder policy; it must not automatically become a permanent prohibition. [P1, P3]

A proposed confirmation should describe the concrete recommended set, affected repository, material consequences, user-selected deviations, and qualification limits. It should support accepting the set, changing particular choices, or rejecting it. “Apply good defaults” can authorize preparing a default plan and presenting that confirmation; it should not conceal materially different behavior inside an undefined package. Existing session authority should be respected, and repeated confirmation of the same unchanged authorized plan should be avoided. [P1, P2]

Before implementation, the stakeholder needs to decide which harms can justify refusal, which concerns warrant a warning and informed override, how policy applicability is established, and what happens when the catalog cannot classify a novel choice. Nothing here assumes that stronger protection is always less harmful: a constructed misconfigured gate could prevent all intended work. This is a counterexample to a monotonic “more strict is always better” assumption, not evidence about any platform.

### Readback, drift, rollback, and qualification

I propose four separate comparisons: the requested concern against the plan; the plan against accepted authority; the intended configuration against readback; and claimed behavior against observed outcomes. A successful write and matching readback answer only part of the problem.

An application interface could consume a plan, the accepted revision, expected starting state, and necessary authorization. It could return applied changes, failures, readback, and qualification evidence. Concurrent changes or unavailable reads should be represented explicitly. The domain must not assume multi-setting operations are atomic.

Rollback should be conditional: retain enough prior state to propose restoration, identify changes that cannot safely be reversed, and check whether others changed the same surface before restoring it. Restoring values need not erase effects already caused by those values. If reversal cannot be assured, disclose that in the plan rather than calling an untested procedure rollback.

Drift needs meaning, not only detection. A difference may be intentional user customization, a policy violation, a stale recommendation, or an unknown source of change. Proposed responses include reporting, requesting a new decision, or repairing within already established authority. Automatic repair must not be the default consequence of discovering a difference.

## Constructed CI decision horizon

This is a proposed research sequence for the concrete CI concern, not a hardened CI specification or claim of platform support. [P1]

1. Describe the repository characteristics that matter to checks: languages and tooling, content types, layout, generated outputs, and trust-relevant execution circumstances. Keep inferred characteristics distinct from observations.
2. Translate the user's concerns into bounded behavior claims. “Extensively hardened” is not yet an acceptance criterion; candidate dimensions include protecting sensitive material during execution, resisting unreviewed execution changes, getting applicable check coverage, and enforcing an agreed acceptance decision. These dimensions remain proposals for stakeholder review.
3. Identify candidate checks and execution strategies, with reasons tied to those claims. Do not assume every repository benefits from the same checks or maximum strictness.
4. Examine the connection between each intended check and each consuming gate: identity, event coverage, result interpretation, absence, failure, replacement, and any permitted exception path. Verify actual platform semantics later.
5. Present a recommended set and meaningful alternatives, then obtain the confirmation required by the established workflow.
6. Apply only if later authorized; compare readback with the plan and challenge the behavior claims using agreed cases.

The first distinguishing cases should include: a check that fails; a check that produces no result; a legitimate content-only change; a check renamed without updating its consumer; two independent checks with confusingly similar identities; and a permission or trust change that affects execution. Their expected outcomes are open decisions where the supplied concern does not determine them. These cases are chosen to challenge fit and connection, not to establish an exhaustive threat model.

## Smallest evidence that could choose among the proposals

A bounded next experiment could use the same frozen knowledge and six constructed cases across all three designs. Keep the first four cases visible during authoring and reserve two conditional variants for evaluation. The exact cases, adjudicator, cost budget, and acceptance threshold require agreement; no numeric threshold here is an established policy.

| Hypothesis | Distinguishing evidence | Failure that would change the design |
| --- | --- | --- |
| Short trigger guidance can retrieve complex relevant detail. | Agent produces an explanation including each adjudicated consequential interaction without being told which entries to open. | Omission recurs despite the necessary knowledge being present. |
| A relation model earns its maintenance burden. | B catches an important dependent change that A misses, without introducing spurious requirements. | Similar output quality with higher authoring effort, or recommendations promoted to constraints. |
| Behavior scenarios detect a gap that settings readback cannot. | A constructed system with matching readback violates a selected behavior claim, and the scenario reveals it. | Scenarios assert configuration shape without observing the stated outcome. |
| User freedom survives recommendations. | A permitted unconventional choice yields alternatives and a truthful tradeoff explanation. | The agent refuses solely because the choice differs from the recommended set. |
| Unknown policy remains unknown. | A potential-harm case produces a narrow stakeholder question and preserves independent progress. | The agent invents a prohibition or silently assumes permission. |
| Freshness handling is selective and sufficient. | Change one supporting mechanism claim or policy and observe which recommendations and evidence are reconsidered. | Relevant conclusions remain trusted, or every unrelated conclusion is needlessly discarded. |

A case scorer should assess outcomes from the frozen problem and the case's supplied policy, rather than rewarding resemblance to the catalog's own wording. Record both missing consequential interactions and irrelevant recommended work. Ask a reader to recover why each proposed change exists, what could justify an alternative, and what remains unverified. Measure authoring and review effort alongside agent output quality. Cross-case success would support only the tested claims; broader coverage would remain a separate increment.

## Minimal core and useful interfaces

A **proposed** minimal Skill could say, in substance: invoke this equipment when creating a repository, preparing good defaults, changing consequential repository behavior, or explaining related settings; gather the concern, applicable policy, and relevant observations; retrieve the catalog entries and interactions; recommend a concrete set with alternatives and reasons; resolve consequential unknowns; obtain required confirmation; and separate readback from behavior qualification. The core would point to maintained resources for details rather than carry a universal matrix. This is a design sketch, not text approved for installation. [P1, P2]

Useful proposed interfaces, without assigning an owner:

- **Catalog contribution:** concern or setting identity, applicability, rationale category, supporting sources, interactions, counterexample, freshness conditions, and proposed consumer. Review should ask whether the entry changes a decision rather than merely adding description.
- **Recommendation request:** user concerns and chosen overrides, repository observations with uncertainty, applicable policy references, platform context, and requested scope. The response is a concrete plan, explanation, alternatives, unresolved questions, and evidence dependencies.
- **Application request:** accepted plan revision and applicable authority, expected starting state, and permitted operation scope. The response records actual changes and failures. Following local vocabulary, semantic planning and actuation remain distinguishable without forcing them into separate implementations. [P4]
- **Qualification result:** behavior claim, relevant candidate and observation identities, method, observed outcome or explicit lack of observation, and limits. It should be independently reviewable enough that a downstream consumer can identify stale evidence.
- **Consumer feedback:** a reproducible mismatch between a catalog claim and an observation, its conditions, and the decision it affected. Feedback can propose a correction without silently replacing policy or approving a new default.

A future producer would need to supply a maintained source, a precise invocation condition, a reviewed revision, supported contexts, completion criteria, and current behavior evidence. A future consumer should load that revision before dependent work and return corrections through the agreed path. Ownership, source location, plugin membership, publication, installation, and consumer adoption remain open. This report captures the proposal; it does not claim procedure capture or downstream adoption is complete. [P1, P2]

## Stakeholder decisions still needed

The most useful first decision is which concrete outcome will make the first increment worthwhile: a recommended configuration for a new repository, assessment of an existing repository, or the narrower CI-to-gate concern. These are distinct evaluation horizons, even if later equipment supports all three.

The next decision is the policy treatment of harm: who establishes it, what evidence is required, which actions can be refused, and which may proceed after an informed user choice. Closely related is which existing policies can actually constrain an otherwise arbitrary configuration and how their applicability is shown. [P1, P3]

After those decisions, choose the smallest supported repository/platform contexts and the acceptable cost of qualification. Then compare the representations using evidence that can change the choice. Assigning a maintainer, selecting packaging, or installing a convention before that comparison would settle questions this research was asked to leave open. [P1]
