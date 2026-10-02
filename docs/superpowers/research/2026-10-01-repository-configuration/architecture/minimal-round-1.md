# Repository configuration as a two-operation consultation

I propose one deep module that turns a repository concern into a concrete decision and, when separately requested, carries that decision through its existing owners. Its two entry points are **advise** and **carry out**. The caller supplies intent and chooses among consequences; the module discovers the relevant settings, explains their interactions, refreshes evidence, routes authorized work, and accounts for incomplete results. This is a proposed interface for Agent Equipment, not a selection of its final name, source home, or packaging.

The current increment is an isolated architecture proposal. Its supported inputs are the frozen research, the constructed request, the comparison cases, and current source ownership declarations. Acceptance is a complete caller interface, defensible internal seams, explicit limitations, and an experiment that could disprove the proposal. Nothing here qualifies an implementation, changes repository policy, or selects the first alpha.

## The complete caller interface

**Advise(repository, intent)** accepts a repository identity or a description of a repository to create, plus ordinary language describing a desired outcome, review question, or exact setting choice. Preferences, deliberate exceptions, and supplied policy may accompany it. These are optional context, not a compulsory questionnaire or configuration language. The module recovers discoverable facts and asks only about consequential intent or authority it cannot recover.

The result is a **decision document**: recommended changes or deliberate preservation, material alternatives, why each matters, assumptions and applicability, and the next decision. Existing state appears only where it changes the recommendation. Evidence and proposed application details are available behind that readable account. A documented limitation must identify the unsupported claim and useful remaining advice; an unknown setting must not become an invented supported setting.

**Carry out(decision, instruction)** accepts a returned decision and an actual instruction selecting work. The decision is a retained document or conversation artifact, not a bearer credential. The instruction may authorize a subset, impose a constraint, or request readback/resumption of previously authorized work. The module resolves it to concrete effects and existing authority before proceeding. It returns the completed effects and evidence, unchanged or incomplete work, and any next decision.

These are two operations, not two opaque shortcuts hiding a public orchestration protocol. Callers do not select knowledge records, compose control recipes, name provider endpoints, refresh sources, construct recovery manifests, or invoke each downstream skill themselves. They also do not need to enumerate every setting related to their concern. Discovery and those handoffs are implementation duties.

The unavoidable interface rules are short but substantive:

- Advice alone changes no target configuration. It can prepare reviewable local artifacts within its task authority.
- A recommendation is neither binding policy nor application authority. A retained decision can become stale; the module rechecks affected assumptions before an effect.
- A deliberate supported choice is preserved unless an applicable policy conflict or evidenced active harm needs the treatment the operator has selected. Disagreement with a recommendation is insufficient. The unresolved harm policy cannot silently become a stricter default.
- Completion is scoped to the requested claim. Configuration readback, exercised hosted behavior, and local equipment invocation are separately reported.
- Work is not an atomic transaction. A partial or unknown result stays visible; repeating “carry out” first reconciles uncertain prior effects rather than blindly retrying them.

There is no mandatory session-registration call. A new chat can present the decision document; missing evidence is reacquired or marked unavailable. A terse instruction that cannot identify the selected decision produces one concrete clarification. Failed access, contradictory sources, missing authority, unsupported settings, and competing ownership are results with a next action, not exceptions that force callers to learn implementation internals. Advisory work can continue on unaffected claims. Application stops only the dependent effects.

Latency belongs to the interface too: focused advice should inspect the implicated setting family and consequential dependencies, not perform an automatic whole-repository audit. A broad creation request justifies broader discovery. Expensive source refreshes or authorized hosted experiments must be disclosed when they become necessary.

## Four uses and one illustrative result

**New repository:** “Advise on creating a public Python/plugin repository for a solo maintainer with agent assistance.” The module proposes a coherent initial configuration, calls out decisions such as intended review independence, and prepares concrete defaults for confirmation. It does not infer the contribution policy, paid-service budget, or eligible human reviewer from the language alone. A subsequent creation instruction goes through a qualified provider creation route if that route is supported; otherwise the module returns the prepared configuration and the unavailable action.

**Defaults:** “Recommend sensible defaults here; keep our accepted contribution model.” The module inspects that model and presents a small related set with rationale. “Default” is a suggested starting choice, not an already adopted rule, and does not erase deliberate settings.

**Focused concern:** the brief's public Python/plugin repository has partial checks and no CodeQL default setup; the request is to increase CI security and prepare a recommendation. A possible output is:

> I recommend first identifying which current checks establish the behaviors you want to require, then adding only demonstrated gaps to the merge requirements. The partial-check inventory does not yet show that every important failure can block a change.
>
> Assess CodeQL coverage for the relevant Python and workflow content, alongside the checks already owned by this repository. Configuration alone would not demonstrate successful analysis or useful coverage. If enforcement is selected, stage it after the relevant producer and contribution events produce the expected results.
>
> Retain the current approval choice while we determine the intended review model and eligible reviewers. Agent assistance does not by itself establish an independent reviewer or a counted approval.

This is illustrative conditional advice, not a completed recommendation from a source audit. The internal follow-through would name concrete check producers, settings, coverage claims, and evidence needs once observations support them. It would assess Actions admission separately from whether checked-in references already use pins.

**Custom override:** “Keep a temporary no-bypass freeze, and permit this supported action source despite your narrower recommendation.” The module preserves both choices, identifies actual applicable policy, and explains relevant consequences. It does not “repair” the freeze for liveness. If a policy conflicts with the requested exception, it names the policy and needed decision; it does not silently adopt the exception or substitute its preferred configuration.

## What the implementation owns

The seam sits at the user's repository decision. Internally the module performs context acquisition, scoped research, reasoning, proposal preparation, and authorized outcome coordination. The leverage comes from owning the connections: intent to behavior, behavior to controls, controls to effective target state, and requested effect to its existing owner.

I would keep the reasoning agent-led, supported by private deterministic helpers for observations, identity comparisons, and resumable effect accounting. The maintained knowledge would be concise, source-linked explanations of supported decisions and failure cases. Their prose can discuss interactions without requiring a universal setting schema or relation language. An internal index retrieves relevant explanations; it is not another interface the caller must learn.

Each consequential recommendation retains its particular dependencies: applicable policy, source claims, target observations, and any reviewed procedure revision. This is a bounded dependency record for the decision, not a proposed global knowledge graph. A setting change, documentation conflict, or procedure correction invalidates the affected recommendation. It does not mechanically invalidate unrelated advice. Maintainers can inspect those records to find consumers of a corrected claim.

The module must disclose its supported setting families. It can investigate an arbitrary request using public sources and existing owners, but it cannot promise executable support for every GitHub setting. Unsupported application gets useful advice plus the exact missing route. Crucially, extending support changes maintained equipment; it does not require each caller to author a plugin, recipe, or schema.

This concentrates knowledge and recovery in one place. Deleting the module would put those duties back into every caller, so it passes the deletion test in principle. That depth remains a hypothesis until evaluation shows the hidden work is actually performed reliably.

## Dependencies, adapters, and existing owners

Local repository files and helper processes are **local-substitutable** dependencies. Test complete requests against temporary repository trees and real local readers. Do not expose a filesystem interface merely because a mock is convenient. Policy interpretation and comparison are in-process work. Substitutable process failure fixtures should exercise unavailable tools and malformed output through the public operations.

GitHub is **true external**. An internal seam is justified by two concrete adapters: an authenticated CLI/API adapter for selected observation and configuration operations, and a replay/fake adapter for controlled responses, errors, and state changes. Both preserve unavailable observations rather than manufacture false values. The production adapter uses the existing authenticated environment; it does not introduce a credential store. Replay establishes behavior of this equipment under supplied observations, not GitHub enforcement. Live qualification of any selected hosted claim remains separate.

The private provider interface should grow only with supported effects and observations. Do not expose a general arbitrary-request mutation endpoint as the module's shortcut around ownership. Tests inject the adapter internally; callers still use the same two operations.

An existing configuration writer is an owner to integrate with. If Terraform or an App already owns a field, the module proposes the change in that maintained source and coordinates its normal route. It must not compete by writing the hosted field directly. When ownership cannot be determined, advice can explain the proposed value, but the corresponding effect awaits resolution.

Current sources support preserving these divisions: Versionkeeping owns Git mechanics; Mergecraft owns PR authoring/publication and lifecycle; Tricritical owns its review roles; Rolecasting owns delegation/model selection; Artifact Customs owns applicable inbound third-party assessment and policy. The configuration module coordinates their established interfaces when needed. It neither recreates their checks nor treats successful invocation as permission. Security judgments and release authority remain with their existing owners. A missing installed owner is a capability limitation, not permission to substitute an unqualified source-stage route.

If no current owner covers a particular setting mutation, the selected design would need a narrowly qualified actuator or an explicitly selected existing provider route. That is new scope to justify, not authority obtained from this paper interface.

## Shared cases as observable obligations

| Case | What callers should receive |
| --- | --- |
| Legitimate unconventional choice | Preserved choice, material consequences, and no invented prohibition. |
| Freeze versus accidental deadlock | Different recommendations from different stated purposes, even with identical settings. |
| Same check name, changed producer | Affected binding reconsidered; the name alone never preserves prior confidence. |
| Skipped/missing checks or event mismatch | Explanation of what executed and what can satisfy the requirement; no generic “green means covered” claim. |
| Admission permits unpinned actions; source is pinned | Separate descriptions of present source practice and permitted future input. |
| Scanner enabled without claimed coverage | Configuration observation retained; analysis and enforcement claims remain unqualified. |
| Conflicting documentation | Both relevant claims and a narrow applicability question; no invented reconciliation. |
| Existing configuration writer | A source change through its owner or an explicit unresolved ownership decision. |
| Corrected procedure invalidates a consumer | Affected decision revisited using the revised procedure, preserving unrelated decisions and historical evidence. |
| Partial application/readback unknown | Confirmed effects, unknown effects, and a reconciliation path; no global success or automatic rollback. |
| Local discovery versus hosted enforcement | Two independent evidence claims and no substitution between them. |

Recovery is the sharpest obligation. Suppose source preparation succeeds, a provider write times out, and readback is unavailable. The module records source preparation as observed, the hosted effect as unknown, and postpones dependent gate activation. It does not restore guessed old state. A later invocation reads the actual state and changed owner inputs before continuing. Restoration, if selected and authorized, must account for coupled source and contributor guidance; settings alone may be insufficient. The history follow-up's DCO example motivates this concern without making its exact rollback sequence universal.

## Source home and integration choices

My preferred integration to test is agent-hosted equipment: a discoverable Skill providing these two operations, with private references/helpers sufficient to perform the hidden work. That is a delivery hypothesis derived from the conversational interface, not a requirement of the architecture. A document-only delivery would need to show equivalent reliable execution and recovery; an MCP server would need to justify the extra lifecycle and deployment cost. Neither gains an advantage merely by exposing two method names.

The candidate can begin as repo-carried equipment while its source owner and supported contexts are decided. A distinct Plugin could later carry the same module without adding it to the current Provingkit Slate. Extending an existing Plugin is sensible only if its ownership fits; the reviewed READMEs do not establish one current owner for this whole task. Generic promotion to Agentworks remains a separate decision.

`docs/release-artifact-projection.md` distinguishes canonical sources from installable projections. `docs/preview/install-and-update.md` distinguishes installed bytes and fresh discovery from actual invocation. Any selected delivery must retain those distinctions and its applicable publication owner, without importing whole-Kit release claims. `capturing-agent-procedures` makes the maintained procedure, invocation condition, reviewed revision, consumer binding, and correction path part of completion. This proposal and the historical research remain evidence, not installed policy.

## Qualification, tradeoff, and possible alpha

A small qualification program should run the shared cases through **advise**, then selected stale/partial/retry cases through **carry out** using temporary trees and the replay adapter. Independent assessment should judge missed consequential relationships, false prohibitions, unexplained assumptions, preservation of deliberate choices, and truthful completion. Verify discovery with supported prompts and nearby prompts that should not invoke this equipment. When application is in scope, qualify only the selected provider effects and hosted behavior claims through separately authorized fixtures. Finally verify the maintained revision's installation and a useful invocation in the selected harness.

The discriminating experiment is a cold-start comparison using identical facts, sources, actor policy, and provider replays for all designs. Give each a CI concern, then change the check producer without renaming it, correct a consumed procedure, and simulate a timed-out write. Measure both answer correctness and everything the caller must supply, learn, or manually coordinate. Also measure the maintainer work needed to add that correction. This design loses if its apparently small interface produces materially more omissions or requires the caller to reconstruct its hidden process.

The strongest objection is that this is a broad agent coordinator disguised as a deep module. Free-form requests can conceal an enormous implementation, and a decision document can become an unmanageable state machine. The proposal earns its shape only if supported families stay explicit, helpers own repeatable mechanics, and public-operation evaluations demonstrate consistent reasoning and recovery. Minimal caller interface shifts complexity to maintainers; it does not abolish it. A more explicit caller contract may outperform it for frequent automation, exhaustive policy comparison, or repeated arbitrary settings.

A possible first alpha is concrete recommendations for one selected GitHub repository/actor context and a small set of CI/review settings, with apply explicitly unavailable. Another scope decision could add one qualified configuration operation. These are options for the operator, not selections made here. The full design still must account for creation, configuration, review, defaults, deliberate overrides, and authorized recovery as support expands.

## Evidence and exposure record

I verified the common brief against SHA-256 `430c73eba6e5352bcca8b3668c3b1771d0cf8e0d257fa95d8be118df4cd430fb`. The checkout was clean at research commit `70879ae2ea94fac8708ab77051d08ded9429fce4`, on `nisavid/research/repository-configuration`, with a non-shallow graph. No upstream is configured for that branch, so an upstream-relative unpublished count was unavailable. I inspected local push configuration only; no publication or remote observation ran.

Actual source exposures were `AGENTS.md`, `CONTEXT.md`; `research-synthesis.md`, `method.md`, `conceptual-follow-up.md`, `history/round-2.md`, `github/round-2.md`, `follow-ups.json`, and `verification.md` under the frozen research directory; relevant sections of the Versionkeeping, Mergecraft, Artifact Customs, Rolecasting, and Tricritical READMEs; top-level keys of their topologies and Versionkeeping's ownership declaration; `docs/release-artifact-projection.md`; and installation/verification portions of `docs/preview/install-and-update.md`. Some broad batched output was truncated, so focused rereads supplied the sections used above. Directory listings exposed additional filenames, not their contents.

I read `codebase-design` and its `DESIGN-IT-TWICE.md`/`DEEPENING.md`, `capturing-agent-procedures` and its producing reference, and the installed Versionkeeping `checkpointing-and-publishing-git-work` skill's read-only policy. Ambient harness instructions and the injected memory summary were visible; I opened no memory file. I read no peer architecture artifact, initial research report, underlying private transcript, live provider state, or new external documentation. No subagent was spawned. Only this report was written. Platform statements are attributed to the frozen research; all proposed equipment behavior, examples, recovery, and qualification results are hypothetical.
