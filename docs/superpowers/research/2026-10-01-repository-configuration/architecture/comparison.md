# Adaptable repository configuration through one focused procedure

The design is one discoverable repository-configuration Skill in Mergecraft, supported by concise decision guides and small executable helpers where they earn their upkeep. The caller supplies an ordinary task; the equipment discovers relevant context, explains consequential choices, and uses existing tools and procedures to complete authorized work. A setting does not need a catalog entry or bespoke actuator to be usable.

The operator selected the focused Skill and guides, end-to-end workflows, contextual judgment, live organization/private qualification alongside personal/public use, and all three local clients. Mergecraft placement follows the operator's suggestion and a separate source assessment. The behavior below has not been implemented or behaviorally compared. The [choice records and method](README.md) distinguish direct answers, the placement suggestion, and the coordinator's design judgment.

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

Maintain the new Skill under `plugins/mergecraft/skills/`, with a descriptive name settled by the source contract. Expand Mergecraft's declared responsibility to GitHub repository configuration as well as Issue/PR authoring and the PR lifecycle. Its current roster does not already implement general repository configuration. The [Mergecraft fit assessment](mergecraft-fit.md) compares this addition with separate distribution and identifies the source changes it requires.

This places related GitHub judgment with existing forge-facing equipment and uses an already supported Plugin identity. Sharing that identity also couples updates to Mergecraft's governed content and delivery. A separate Skill or Plugin would become useful if configuration needed its own audience, installation choice, or release cadence; the current task does not establish that need. The earlier [packaging assessment](packaging-feasibility.md) considered only standalone Skill and independent Plugin routes. It remains evidence about those alternatives, not a complete placement comparison.

Add the public Skill contract, actual calls, discovery metadata, and appropriate operation ownership to Mergecraft's topology and validation. Update its manifest, adapter, README, root discovery, responsibility descriptions, behavior evidence, and ordinary content lock through the owning procedures. Use ordinary native-tool operations where they suffice; a finite Skill roster is not a requirement for a per-setting custom actuator. The existing projection policy carries Skill resources to Agent Plugins/Codex, Claude Code, and Cursor. This source evidence does not establish successful installation or invocation of the future candidate.

Keep routine relation handling, PR readiness, and merging focused on their own tasks. A merge request does not implicitly authorize weakening protection or a whole-repository assessment. Use Versionkeeping for Git effects and Mergecraft's publication owner when a PR is needed; use the focused CI adapter only for its diagnosed-failure contract. Compose review and security expertise where the actual concern warrants it. Invalidate affected observations when a configuration change matters to an existing consumer, such as the relation owner's closure-setting cache.

The implementation map must settle the Skill name, exact Mergecraft alpha identity, supported deployment route, and client surfaces before installation. Preserve prior provider and recovery information, verify the changed member and its affected existing consumers, detect shadowing, and demonstrate fresh useful invocation in Codex, Claude Code, and Cursor. A member alpha is not a whole-Kit Release. A listed Skill is not an invocation; an invocation is not hosted enforcement.

## Qualification and implementation-map contract

Evaluate complete useful examples of all five selected workflows. Include already-authorized and uncataloged changes, deliberate unconventional choices, an intended freeze, missing permissions, inherited-policy unknowns, an existing writer, contradictory sources, procedure corrections, changed check producers, skipped/missing results, no-op, and partial/unknown application. A second evaluator must assess actual traces rather than only final prose. Hold out some combinations and relationship hints. A recurring material failure must change the candidate before acceptance; “use judgment” is not sufficient remediation.

Live qualification must include personal/public use and organization/private use. The qualification contract names representative repositories, plans, actors, permissions, inherited controls, fixture authority, and useful enforcement cases. It need not assume every owner/visibility/plan combination, but synthetic or replay fixtures cannot discharge the selected live organization/private requirement. Unavailable access leaves that obligation open. Use the smallest authorized hosted fixtures needed for the claims, isolating a claimed rejection from unrelated blockers. Do not create a universal numeric score or hardening threshold by assumption.

The separate [Wayfinder implementation map](https://github.com/nisavid/provingkit/issues/374) charts the route to the locally deployed alpha before this design panel ends. Its Notes explicitly carry delivery work into the map. Its five tasks connect the design to maintained procedure capture and discovery, seeded guidance, earned helpers, behavioral evaluation, independent current review, publication, local deployment/recovery, and useful consumer invocation. Each qualification obligation belongs to its delivery stage: implementation closes on pre-deployment evidence, deployment establishes published and installed identity, and the final consumer task establishes useful fresh invocation in all three clients. Keep unresolved precise questions as tickets and broader uncertainty as fog. Charting that map does not start implementation or change live settings.

## Evidence and next decisions

The [minimal](minimal-cross-examination.md), [flexibility](flexible-cross-examination.md), and [caller](caller-cross-examination.md) follow-ups independently addressed the common exchange. They retract the implied bespoke-actuator requirement and mandatory proposal ceremony, and converge on adaptive execution with focused support. This is cross-informed design judgment, not three runtime validations. Their exact identities are retained in [the report manifest](cross-examined-reports.json); [the method](method.md) records isolation and later exposures.

The source and qualification contracts now own the precise Skill name, member alpha identity, installation/recovery route, representative live fixtures, client surfaces, and phase-specific acceptance cases. These sharpen the selected design; they do not reopen its capability scope or substitute source conformance for behavior. Final review evidence and the retained map snapshot are linked from [verification](verification.md).
