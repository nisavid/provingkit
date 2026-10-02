# Adaptable repository configuration through one focused procedure

I recommend one discoverable Skill that helps an agent complete repository-configuration work, supported by concise decision guides and small executable helpers where they earn their upkeep. The caller supplies an ordinary task; the equipment discovers relevant context, explains consequential choices, and uses existing tools and procedures to complete authorized work. A setting does not need a catalog entry or bespoke actuator to be usable.

This is the cross-examined recommendation for the human architecture decision. The first-alpha capability and contextual-judgment policy are accepted. Architecture, source/packaging, qualification contexts, and local deployment targets still need their actual decisions. The proposed behavior below has not been implemented or behaviorally compared.

## What the alpha must do

The operator selected end-to-end GitHub workflows: create a repository, assess existing settings, adopt recommended defaults, make a focused change, and add project-specific CI hardening, including authorized application through existing tools. Coverage limits must be explicit; cataloging every GitHub setting is not a release prerequisite. The [choice record](operator-choices-1.json) preserves the actual answers.

The operator also selected contextual judgment. Explain consequential tradeoffs and honor informed choices. Cite actual applicable policy when it constrains a choice. Intervene for concrete active harm, such as exposing privileged CI credentials to untrusted code. An intentional freeze is valid; an accidental deadlock calls for clarification. A nondefault choice, a low assessment score, or disagreement with a recommendation does not create a prohibition.

## The three architectures compared

The first three isolated reports converged on a conversational proposal backed by maintained guidance. Their different document names and entry-point counts were interface variations, not three materially different architectures. Two additional isolated variants made alternatives concrete before peer exchange. All three lanes then consumed the same [exchange](exchange-1.json), actual operator choices, and [comparison cases](comparison-cases.json).

| Architecture | Where the maintained work lives | Strongest case for it | Main cost |
| --- | --- | --- | --- |
| Adaptive procedure | Agent instructions, source-linked decision guides, task evidence, native-tool use, and focused helpers | Unfamiliar settings and varied user intent fit without extending a central model first. | Retrieval and judgment may miss interactions or handle recovery inconsistently. |
| Structured decision knowledge | Applicability predicates, relationship records, explanation, evaluator bindings, and their consumer | Known relationships and repeated comparisons become explicit and reproducible. | Incomplete relationships can create false confidence; data, prose, and evaluator semantics must stay aligned. |
| Operation-specific automation | Each operation's observation, preparation, transitions, application, readback, and fixtures | Repeated consequential updates can preserve fields and reconcile uncertain effects consistently. | New operations and platform changes require maintained code while policy and novel cases still need judgment. |

The [knowledge variant](knowledge-variant.md) shows a small record and consumer, rather than assuming a universal solver. The [automation variant](automation-variant.md) shows a bounded required-check operation, rather than assuming a cross-system transaction engine. Both are viable alternatives for repeated problems. Neither currently has evidence of enough benefit to make it the mandatory foundation for every setting.

I favor the adaptive procedure because it fits the requested arbitrary setups and the accepted breadth without making routine changes wait for a modeled setting or new operation module. Focused checks and operation helpers remain available inside it. The recommendation changes if held-out evaluation shows repeated missed relationships, unstable mechanical comparisons, or incorrect recovery that a structured or automated alternative reliably prevents at an acceptable maintenance cost. That comparison belongs in qualification; no performance advantage has been measured here.

## The proposed interface

Invoke the procedure for repository creation or configuration, adoption of defaults, configuration review, or a concern that requires repository controls. Ordinary code edits and generic code review do not automatically trigger a whole-repository assessment. GitHub is the first provider; additional providers require their own supported knowledge and controls.

The caller supplies a target or intended repository, the desired outcome or exact change, and known constraints. The agent recovers discoverable facts and asks only about consequential choices or missing information it cannot discover. Focused requests inspect their relevant controls and consequential dependencies; broad creation or defaults requests justify broader discovery. The result states the assessed scope and its limits.

A concrete proposal is useful when choices remain or work needs continuity. It is not a compulsory phase the user must approve for an already specified, authorized change. Newly proposed defaults are a concrete related set with rationale for confirmation where that choice has not already been delegated. Preserve authority and settled preferences from the active task.

The procedure keeps four practical responsibilities together:

1. Understand purpose, actual policy, relevant repository content, actors, available control surfaces, and existing configuration owners.
2. Connect the desired behavior to concrete choices, explain material interactions and alternatives, and preserve uncertainty where it affects the decision.
3. Prepare and perform the authorized native change through the existing owner, refreshing affected assumptions before effects.
4. Reconcile uncertain outcomes and report what was actually verified, including useful remaining work or a specific blocker.

These responsibilities describe behavior; they do not require four Skills, a fixed workflow engine, a universal record schema, or a new approval protocol.

## Knowledge and executable support

Maintain a small index and focused decision guides. A guide explains supported circumstances, why a setting matters, consequential neighboring choices, alternatives, source references, and discriminating examples. Fields and structure should serve retrieval and maintenance; every setting need not conform to a comprehensive ontology. Keep repository policy and accepted exceptions with their actual owner.

The initial knowledge should cover creation and contribution paths, effective restrictions and review eligibility, check identity and coverage, project-specific analysis and matching gates, Actions trust and permissions, dependency/secret controls, existing writers, and application/readback limits. The implementation must choose useful depth and make its unreviewed long tail visible. The [research synthesis](../research-synthesis.md) and lane sources provide evidence, not a universal baseline to copy.

An unfamiliar setting follows current primary documentation, available tool semantics, target applicability, relevant policy/ownership, the minimal intended change, and useful verification. Catalog absence is not a prohibition. A supported native tool can carry a task-specific change without new equipment code; that observed result does not qualify every operation the tool exposes. Unavailable controls, unresolved consequential semantics, concrete harm, or an actual policy/authority conflict remain real limits.

Add a deterministic helper where recurring mechanics justify one, such as comparing required-result producers or preserving enclosing configuration during an update. A helper reports its supported scope and unknowns; it does not infer semantic test coverage from names. A valid failure condition survives a change of tool. An unsupported parser or missing helper field can instead justify a researched alternative that preserves the underlying invariant.

Local files and processes use temporary repositories and real readers in tests. Where maintained code interacts with GitHub, live CLI/API and replay adapters justify an internal seam. Ordinary agent-native tool use can be evaluated through harness replays rather than wrapping every tool in another client. Replay validates this equipment's handling of supplied behavior; provider behavior remains a separate observation.

## Concrete behavior that distinguishes the design

For an already authorized wiki or Discussions toggle, verify target semantics and relevant ownership, read the current state, make the minimal supported native change if needed, and read it back. Do not demand a new catalog record, actuator, or repeated apply instruction. Report an unchanged value as a no-op only when observed.

For CI hardening, inspect the project's actual language, layout, content, contribution events, and desired failure claims. Choose suitable checks and analysis, then decide which results and alert thresholds should block changes. A renamed producer, a skipped validator, and overlapping checks require different reasoning. Source pins and permissive Actions admission are different facts. Enabling CodeQL, completing useful analysis, and exercising a selected merge gate are different claims. Existing Plugin/content validators remain relevant where code analysis does not establish their contracts.

For a timed-out write after successful source publication, preserve the confirmed source result and mark the hosted effect unknown. Reconcile it during the active task before dependent changes; do not blindly replay or restore guessed old state. If readback later matches, report the observed state without inventing causation. Preserve another owner's intervening changes. Refresh a corrected procedure's affected assumptions without discarding unrelated choices or authority.

A source or documentation revision can change a relevant premise. Retain consequential source/procedure identities and target observations with the task result, and reconsider affected claims. Hash changes alone do not establish semantic impact; a universal expiration interval is not selected. Conflicting first-party sources, such as the retained Copilot approval case, stay visibly unresolved until sufficient target evidence supports a narrower conclusion.

## Source and deployment decision

The panel recommends Provingkit-owned canonical source for the proving alpha. No inspected existing Plugin owns the full repository-configuration concern. Preserve Versionkeeping, Mergecraft, Rolecasting, review, security, third-party-component, and release responsibilities; invoke their maintained procedures rather than copying or bypassing them.

A repo-carried standalone Skill is the smallest packaging option. An independently installable Plugin containing that Skill gives a separate manifest and distribution identity at additional packaging and release cost. Either can preserve the architecture above. The independent [packaging assessment](packaging-feasibility.md) verifies the relevant source at named revisions; it does not qualify either deployment route.

The standalone Skill needs an explicit pinned-source acquisition and installation contract with one semantic owner. Existing global projection conventions do not acquire arbitrary Provingkit Skills end to end. The independent Plugin additionally needs a deliberate source-validation allowance and separately identified artifact projection: current source validation restricts the `plugins/` root to the six known members, and both the projector and maintained installer restrict supported identities. Reusable manifest and containment checks do not make the end-to-end route available unchanged.

I recommend the standalone Skill for the first alpha unless a distinct Plugin distribution identity is itself desired now. A new Plugin must not silently join the current Provingkit Slate or make a one-component alpha a whole-Kit Release. Either route must preserve a single semantic source, existing installation owners, and the current Kit defaults.

The implementation map must settle the source path/name, selected packaging, actual deployment route and client surfaces, and exact alpha identity before installation. It must preserve recovery information, avoid shadowing an existing provider, verify installed bytes and fresh discovery, and demonstrate useful invocation. A listed Skill is not an invocation; an invocation is not hosted enforcement.

## Qualification and implementation-map contract

Evaluate complete useful examples of all five selected workflows. Include already-authorized and uncataloged changes, deliberate unconventional choices, an intended freeze, missing permissions, inherited-policy unknowns, an existing writer, contradictory sources, procedure corrections, changed check producers, skipped/missing results, no-op, and partial/unknown application. A second evaluator must assess actual traces rather than only final prose. Hold out some combinations and relationship hints. A recurring material failure must change the candidate before acceptance; “use judgment” is not sufficient remediation.

Select live qualification contexts and target local clients with the operator. Controlled fixtures can cover unavailable account or organization conditions while keeping their evidence limits explicit. Use the smallest authorized hosted fixtures needed for selected platform claims, isolating a claimed rejection from unrelated blockers. Do not create a universal numeric score or hardening threshold by assumption.

The separate [Wayfinder implementation map](https://github.com/nisavid/provingkit/issues/374) now charts the route to the locally deployed alpha before this design panel ends. Its Notes explicitly carry delivery work into the map, while its first contracts remain blocked by the open design and alpha-context decisions. Its five tasks connect the eventual accepted decisions to maintained procedure capture and discovery, seeded guidance, earned helpers, behavioral evaluation, independent current review, publication, local deployment/recovery, and useful consumer invocation. Each qualification obligation belongs to its delivery stage: implementation closes on pre-deployment evidence, deployment establishes published and installed identity, and the final consumer task establishes useful fresh invocation. Keep unresolved precise questions as tickets and broader uncertainty as fog. Charting that map does not start its implementation or change live settings.

## Evidence and open decisions

The [minimal](minimal-cross-examination.md), [flexibility](flexible-cross-examination.md), and [caller](caller-cross-examination.md) follow-ups independently addressed the common exchange. They retract the implied bespoke-actuator requirement and mandatory proposal ceremony, and converge on adaptive execution with focused support. This is cross-informed design judgment, not three runtime validations. Their exact identities are retained in [the report manifest](cross-examined-reports.json); [the method](method.md) records isolation and later exposures.

The remaining decisions are the architecture, canonical source/packaging, qualification contexts, and local client targets. Precise naming and implementation details can be owned by the implementation map once those choices establish the route.
