# Operation-specific automation behind repository advice

This variant makes executable operation modules the maintained authority for supported observation, change planning, and result accounting. An agent still interprets ordinary-language intent and explains choices. Unlike my initial consultation proposal, prose does not own the sequence of a supported effect: code owns that sequence and refuses unsupported transitions. The strongest small version is a local, finite set of operation modules, not a daemon, universal configuration language, or transaction engine.

The later operator answers select end-to-end alpha workflows: create a repository, assess settings, adopt defaults, make focused changes, and add project-specific CI hardening, including authorized application through existing tools. They also select contextual judgment: explain consequential tradeoffs, honor informed choices, cite applicable policy, and intervene for concrete active harm. Equipment shape and qualification contexts remain open. Changing required checks below illustrates the design; it does not alone satisfy that alpha scope.

## Interface and maintained structure

The human-facing operations remain **advise(repository, intent)** and **carry out(decision, instruction)**. A new-repository request produces proposed settings and remaining choices. A concern such as “increase CI security” discovers related options. An exact override preserves the selected value and explains its consequences. The agent handles those requests through supported operation modules and ordinary research, disclosing which parts have executable support.

The executing agent uses three helper entry points:

1. **Observe** a repository and supported operation family. Return typed facts, inaccessible or ambiguous facts, ownership evidence, and concrete candidate identifiers.
2. **Prepare** selected choices against that observation. Return a finite plan or specific unmet conditions, together with a readable proposed delta.
3. **Advance** a retained plan within the independently established authority. Reobserve prerequisites, perform only its next eligible effect, and reconcile or verify the result.

These helper interfaces are part of the real learning cost. The agent must know the supported family and translate the user's desired result into that family's choices. It does not compose HTTP requests, invent a recovery sequence, or construct each plan record manually. Candidate identifiers refer to returned observations; the operation module owns their validation. Ordinary users never author this representation.

The source structure groups each operation's observation, planning, application, readback, source citations, and fixtures together. Shared code contains only demonstrated common needs such as repository identity, unknown observations, and provider transport. Adding an operation adds a maintained contract the executing agent must learn; counting entry points cannot hide that cost.

The smallest viable alpha therefore needs executable paths for repository creation, a useful selected set of settings changes, and project-specific workflow changes. Assessment and defaults reuse their observations and planning. Creation wraps an existing provider tool and verifies the resulting identity and selected configuration. Workflow authoring stays agent-led through existing development, review, Git, and forge owners; operation code binds the selected source revision, expected checks, and readback. It does not generate every possible CI workflow. These paths must demonstrate complete useful requests in the selected contexts; a required-check writer alone would be too narrow.

| Owner | Maintained responsibility |
| --- | --- |
| Agent-facing prose | Intent interpretation, recommendation rationale, consequential questions, policy-source interpretation, preservation of deliberate choices, and invocation of existing owners. |
| Operation code | Supported inputs, observation parsing, exact target/producer identity, proposed field changes, mechanically checkable prerequisites, allowed transitions, readback comparison, and partial-result handling. |
| Source-linked explanation beside the operation | Platform claims, applicability limits, why each mechanical condition exists, and what the code cannot establish. |
| Repository/operator | Desired behavior, applicable policy, accepted exceptions, actual effect authority, and consequential contextual decisions. |

Code must not contain a universal security baseline or decide that a working merge path always outranks a freeze. Prose must not bypass a failed operation check by emitting a raw mutation command.

## A concrete required-check operation

An illustrative first operation supports replacing the required-check entries in one identified repository-owned ruleset. It preserves unrelated fields, conditions, and bypass configuration. It does not create or merge rulesets, change inherited policy, choose reviewer requirements, or edit workflows itself. Observation of relevant inherited/classic restrictions is still necessary to explain the effective result; inaccessible controlling state limits that claim.

For the brief's CI concern, the agent first maps the requested behaviors to current checks and candidate coverage gaps. It can recommend investigation or new workflow work through existing owners. Code supplies observed check identity and configuration facts. A successful check name is not proof of the agent's claimed coverage, and passing an eligibility predicate is not proof of hosted enforcement.

A selected check-set plan binds the repository, ruleset, old and proposed entries, observed producer identities, relevant source/procedure revisions, and the evidence assumptions supplied for the recommendation. It records which assertions are documentary, controller-observed, or behaviorally exercised. For workflow-job checks, event suitability and skipped/missing-result concerns are carried with the particular check; an event rule must not be applied indiscriminately to external App checks.

Before application, code compares current target and producer identities with the plan. A changed producer under the same name requires reconsideration. Relevant changes produce a new proposal or narrow continuation decision; they do not silently expand the accepted delta. A repeated unchanged request can produce a verified no-op.

If the API route requires sending an enclosing object, the adapter must preserve unrelated observed fields and verify them afterward. A fresh read followed by a write is not atomic conflict protection. Qualification must establish any available provider precondition mechanism; absent one, the operation records its concurrency limitation and refuses known competing ownership. It cannot guarantee preservation against an undetectable intervening writer. Whether that residual risk is acceptable belongs to the selected operation's policy, not an invented global rule.

The limited writer does not finish an entire CI hardening workflow alone. Source revisions go through their source owner, review, Versionkeeping, and Mergecraft as applicable. The agent coordinates those prerequisites before asking this operation to activate the selected checks. Its recommendation can include scanner setup or Actions admission while stating that those effects need their own supported routes.

## Choice, authority, and arbitrary settings

The plan is reviewable data, not a permission token. The agent must bind the actual user instruction and existing task authority to its target and effects. An “authorized” Boolean supplied to a helper is not authenticated permission. The helper enforces the supplied scope mechanically; the harness and established owners supply whatever assurance actually exists.

An intentional freeze remains intact when its purpose is supplied. An accidental unavailable-reviewer gate calls for clarification. An unusual supported setting is not rejected for differing from the recommendation. The accepted contextual policy requires citing actual constraints and explaining consequential tradeoffs while honoring informed choices. Concrete active harm, such as exposing privileged CI credentials to untrusted code, warrants intervention; the module must explain the evidence rather than invent a prohibited-settings list.

An unknown arbitrary setting receives useful source-backed advice and an explicit unsupported-effect result. The agent may invoke an already qualified external owner if one exists; it cannot synthesize a new mutation script and call it part of this equipment's tested support. Adding executable support requires a reviewed operation contract, implementation, fixtures, and qualification. That slower extension path buys a clearer claim about what application actually supports.

If Terraform or an App owns the selected field, direct application is unavailable. The agent prepares the change in that owner's maintained source or returns the exact missing route. Discovering another owner does not transfer ownership to this module. Existing model-selection, review, security, Git, forge, third-party-component, and release owners remain unchanged.

## Partial results, dependencies, and freshness

Each operation defines its own small progression: proposed, ready for an authorized effect, effect uncertain, observed desired state, or stopped for a named condition. These describe this operation's accounting, not a cross-provider transaction protocol. After a timed-out write, **advance** first attempts readback. It never equates timeout with failure or repeats the write solely because no response arrived.

If readback remains unavailable, the result preserves the unknown effect and blocks only dependent work. If state matches the proposal, it records configuration readback, without inventing hosted enforcement evidence. If state differs, it explains the observed difference and requires the applicable recovery decision. Restoration uses the owning operation's qualified route and current authority; it is not automatic compensation across source, settings, and documentation.

Local repository files and processes are local-substitutable dependencies, tested with temporary trees and real readers. GitHub is true external: an internal production CLI/API adapter and a replay/fake adapter justify that seam. Both produce the same explicit unknown/error distinctions. The adapter neither owns credentials nor becomes a public arbitrary-request endpoint.

Procedure corrections and source changes are bound to the operation's claim dependencies. A corrected consumed procedure invalidates the affected plan assumption; an unrelated documentation change does not. Conflicting first-party claims remain unresolved facts. Code can detect a changed recorded revision but cannot decide semantic relevance without the maintained claim explanation or review. This leaves a necessary human/agent judgment seam rather than pretending hashes solve knowledge freshness.

## Qualification and comparison

Replay tests exercise public helper behavior: changed producer with an unchanged label, unavailable observations, changed preimage, skipped or missing results, source/settings pinning differences, scanner enabled without coverage, conflicting sources, existing writer, procedure correction, timeout followed by success readback, persistent unknown, and no-op. They assert externally meaningful plans and result claims, not internal call counts.

Replay demonstrates this equipment's handling of supplied provider behavior. Authorized live qualification must separately establish selected API applicability, preservation semantics, identity readback, and any claimed hosted acceptance or rejection. It should isolate the claimed gate from unrelated blockers. Installed equipment discovery and useful invocation require their own target-harness evidence. None substitutes for another.

Compare this variant with my initial proposal using identical evidence and requests. Introduce a provider schema change and a corrected procedure, then measure missed consequences, caller corrections, safe handling of an uncertain effect, and maintainer work to restore support. The automation variant should show repeatable plan preservation and recovery. It loses if its narrow code support creates frequent dead ends while its authoring and qualification cost exceeds the errors it prevents.

My initial proposal puts more operational judgment into maintained prose and agent execution, with helpers assisting. This variant puts supported effect semantics and allowed progressions into code, with the agent selecting and explaining them. Its strongest advantage is repeatable application and auditable partial outcomes. Its strongest objection is coverage: every new operation and material platform change needs maintained code and tests, while recommendation quality still depends on judgment. A small tool interface does not make that burden disappear.

A Skill with private local helpers is a plausible delivery shape; a distinct Plugin can package it if selected. A server adds little until a real cross-process consumer requires one. Source home, target harnesses, and inclusion in any release remain decisions. Existing projection/publication contracts apply where chosen, without adding this equipment to the Provingkit Slate by implication. Procedure capture must include the maintained source, invocation condition, reviewed revision, qualification limits, installation, and downstream use.

## Actual exposures and limits

I reverified my initial report at SHA-256 `9ea289b5fc91acfabf4e49466061c37ad0553c3a9fad59cba0cabe05947335b7` and reread its opening sections. I also use the instructions, skills, research, ownership declarations, and deployment documents enumerated there. During drafting I received, verified, and read the later operator-choice record `operator-choices-1.json`, SHA-256 `7faee4d71242a99552752e04c5b6e80bc481dad27f97c6143007d7e901fc41c9`; it supersedes the earlier pending decisions. I verified the capability-only snapshot's supplied digest without reading its content. No peer architecture artifact, new research, external documentation, live provider state, or memory file was opened. No delegation or provider experiment ran. Only this report was written. All proposed equipment behavior and qualification outcomes are hypothetical; the operator choices authorize design, not implementation or live changes.
