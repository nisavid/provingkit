# Evidence for adaptable repository configuration

The earlier work retained substantial configuration rationale and verification, but the inspected sources do not provide one maintained method that explains the full setting space across repositories. I would reuse the documented decisions and procedures as evidence, then let a separate design panel decide how agents should retrieve, apply, and maintain that knowledge.

## What the history establishes

[The historical report](history/round-1.md) traces Codiquary's governed release-operations scaffold, Sacrysty's explicit reuse of that scaffold, their later hardening increment, and Provingkit's source-cutover controls. All three repositories were deliberately configured. This does not establish that each configuration remains adequate today, nor that all three were designed to satisfy the same concerns.

The strongest retained examples are concrete. The [Sacrysty](https://github.com/nisavid/sacrysty/issues/8) and [Codiquary](https://github.com/nisavid/codiquary/issues/12) hardening contracts deliberately avoided impossible sole-maintainer human-approval gates and quota-dependent review-app gates. They required observed check coverage before enforcing the new gates. That is a repository-specific decision with rationale, not a universal zero-approval policy. Sacrysty's [maintained DCO provisioning procedure](https://github.com/nisavid/sacrysty/blob/3dd23c4f53da47f83bdf7a82cc98094a4f574501/docs/agents/dco-provisioning.md) and Codiquary's [consumer receipt](https://github.com/nisavid/codiquary/issues/40#issuecomment-5707523713) show how one procedure can be reused while each repository owns its applicable policy and exact configuration change.

Provingkit retained no-bypass protection, source/evidence preservation, and a release freeze during extraction. Its [cutover record](https://github.com/nisavid/provingkit/blob/228844a362fea99b0936973ba55ad3d5d4baea85/release/provingkit/review-evidence/issue-81/538723c92a3103c15a3c835f2161332239a8cb13-daybreak-security-authority-v3.json) records controller observations, with that evidence limitation stated. The history search did not recover equally explicit rationale for every current difference, including conversation resolution, DCO, and Actions admission. Missing rationale in the scoped search is not proof that it never existed.

## What the current Provingkit observations establish

The [dated API and source observations](coordinator-observations.md) agree with the supplied screenshot: PRs are required, approving-review count is zero, and conversation resolution/review freshness are disabled. Twelve app-bound checks are required with strict base freshness and no bypass actors. The enabled extra approval for unattributed Copilot PRs has no effect at zero required approvals under the documented rule; that toggle does not supply an independent approval gate. This is a selective control set, not an absence of protection.

The source workflow has `Proseweaving source contract` and `Installable artifact projections` jobs whose names do not appear in the observed required list. Their omission needs a coverage/policy decision. It does not by itself prove that all their behavior is uncovered by other required jobs. The [history follow-up](history/round-2.md) shows that both names existed before the last observed ruleset update and identifies overlapping source checks. The [conceptual follow-up](conceptual-follow-up.md) requires an isolated behavior claim before treating the omission as a defect.

CodeQL default setup reports `not-configured`; no CodeQL workflow appears in the checked-out workflow directory. That is narrower than an exhaustive audit of every possible scanner. Actions policy permits all actions and does not require SHA pins, while the inspected source workflow itself uses pinned actions and read-only permissions. Settings admission, checked-in practice, and actual runtime behavior must stay distinct.

I have not changed these settings or run enforcement fixtures. Provingkit-specific remedies remain decisions to make from its Python/plugin content, contribution paths, and intended review model.

## Mechanisms that change the design problem

The [platform survey](github/round-1.md) and [cross-examined follow-up](github/round-2.md) describe current GitHub mechanisms, with date-bound primary citations and explicit gaps. Several examples explain why a flat checklist is insufficient:

- Effective restrictions can combine rulesets, inherited policy, and classic protection. Owner type, visibility, plan, actor, and bypass scope change applicability. A new writer also needs to discover an existing App or infrastructure owner before competing with it.
- A required check's name is only part of its meaning. Producer identity, commit, event, coverage, and result interpretation matter. GitHub can accept skipped or neutral conclusions; a filtered-out workflow may remain pending; an ineligible workflow event may not satisfy the requirement. [Required-check semantics](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks).
- CodeQL configuration is separate from actual successful language/build/path analysis, and both are separate from an alert-based merge decision. Scope, thresholds, missing analysis, fork behavior, generated code, and layout need attention when a user asks for harder CI. [CodeQL setup choices](https://docs.github.com/en/code-security/concepts/code-scanning/setup-types).
- A stronger restriction can defeat legitimate work. An unavailable approver, unsupported queue, unrunnable required job, or incompatible merge method can make the workflow unusable. Recommendations need conditions and alternatives.
- Documentation and previews change. Current Copilot configuration docs describe optional approving reviews that may count toward merge requirements, while another first-party page retains contradictory wording. This research does not qualify the feature for a particular repository. A dated source entry still needs conflict handling and live applicability checks. [Copilot configuration](https://docs.github.com/en/copilot/how-tos/copilot-on-github/set-up-copilot/configure-code-review), [review eligibility](https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/approving-a-pull-request-with-required-reviews).

The survey compares Safe-Settings, Repository Settings, Terraform's GitHub provider, and OpenSSF Scorecard. They supply useful configuration, ownership, inheritance, explanation, and assessment examples. Their ability to write configuration or produce a score does not make their policy universal. Their own limitations and model differences must survive reuse.

The survey is not an exhaustive catalog. Environments/deployments, enterprise identity and roles, Pages/domains, packages/releases, transfers, webhooks/deploy keys, Codespaces, storage/billing, and parts of the preview/API surface remain explicitly outside its substantive coverage. The later design must make incomplete coverage legible instead of claiming to know every setting.

## Alternatives to carry into the design panel

The [independent conceptual report](conceptual-first.md) proposes a concern-indexed casebook, a sparse relationship model, and a behavior-first scenario model. They differ in where reasoning and maintenance cost sit: agent retrieval and prose interpretation, explicit relation authoring, or scenario/strategy qualification. They are hypotheses, not selected architecture or accepted domain terminology. After exchange, the [conceptual follow-up](conceptual-follow-up.md) withdraws its initial preference for a casebook: the newly evidenced interactions justify comparing alternatives on common cases, not selecting a richer schema by assumption.

A useful comparison uses the same knowledge and cases, so a better answer is attributable to the design rather than an easier brief. Candidate discriminating cases include an unconventional but permitted user choice, no eligible human approver, a renamed or skipped required job, a scanner enabled without useful coverage, a stale source or conflicting preview claim, an existing configuration writer, and a proposed write that cannot be fully read back. These are paper cases until separately executed; they do not prove platform behavior.

The architecture panel should be free to choose an entirely different shape. It must compare the full caller-facing interface, including required context, ordering, unknowns, failure/recovery behavior, and maintenance work. A short Skill that merely exports complexity to its callers is not a successful simplification. Conversely, these findings do not justify building a general-purpose graph engine, solver, daemon, or universal transaction system.

## Decisions and downstream use

The [live research/design map](https://github.com/nisavid/provingkit/issues/366) owns the decision index. The [first-alpha behavior decision](https://github.com/nisavid/provingkit/issues/372) and [policy and harmful-choice decision](https://github.com/nisavid/provingkit/issues/373) hold the two human questions that the research has made precise. The architecture panel must resolve or explicitly hand forward:

1. What useful first alpha behavior should be supported: explanation, concrete configuration proposals, authorized application, or some combination; and which repository/actor contexts it promises to handle.
2. How to distinguish recommendations, operator preferences, applicable policy, unsupported circumstances, and harmful configurations without making the agent's preference a prohibition.
3. Which representation, interface, maintained source, and existing procedure seams earn their complexity.
4. What evidence is enough for advisory correctness, configuration readback, hosted behavior, local deployment, and downstream invocation, keeping those claims separate.

The user requires a new implementation map before the design panel ends. Its destination is a locally deployed alpha release. That map must connect the selected design and unresolved decisions to maintained source, behavior evaluation, independent review, publication, local deployment verification, and a useful consumer invocation. Charting it does not perform those operations.

This research uses the retained [panel method](method.md). Initial reports are frozen historical outputs; follow-ups and this synthesis own corrections. The source packet is research evidence, not installed guidance, a general security baseline, or a qualified configuration actuator.
