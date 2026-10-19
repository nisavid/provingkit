---
name: configuring-repositories
description: Use when creating a GitHub repository, assessing repository settings, adopting good defaults, changing a repository control, or hardening project-specific CI and its merge gates. Ordinary code edits, test fixes, PR reviews, and already-qualified merges do not themselves request repository configuration.
---

# Configuring Repositories

Deliver the requested repository behavior through current GitHub controls and
the project's maintained configuration. This Skill owns the
`repository-configuration` operation: `create`, `assess`, `defaults`,
`focused-change`, and `ci-hardening`. Its guides explain relationships and
useful starting choices; they do not limit the configurations an informed user
can select.

## Establish the outcome

Recover the user's intent, authorized effects, relevant policy, and existing
decisions. Inspect discoverable facts before asking about them: repository
owner and visibility, project contents, eligible actors, applicable local and
inherited rules, plan/access, actual check producers, and maintained writers
such as Terraform or an App. An assessment request authorizes observation and
recommendations; it does not authorize applying them.

Choose the smallest useful increment and its observable result. For creation
or adopting defaults, propose a coherent set of consequential choices with
their rationale and confirm choices the user has not already authorized.
Continue under settled choices; ask only when missing intent or authority
changes the outcome. A focused authorized change needs no new whole-repository
approval ceremony. Do not infer paid activation, organization policy changes,
deletion, or unrelated repository work from a configuration request.

Read [decision guidance](references/decisions.md) for contextual starting
choices, [GitHub controls](references/github-controls.md) for enforcement
relationships, and [CI hardening](references/ci-hardening.md) when checks or
workflows are involved. Fetch current primary documentation for controls,
plans, APIs, or behavior on which the proposed result depends. Inspect the
target's actual capabilities; documented availability alone proves no access
or effective enforcement. Preserve conflicting evidence until target evidence
or clarification resolves the consequential difference.

## Fit the configuration to the user

Recommend associated settings because they support the requested behavior.
For example, requiring a check also needs a producer that reports for every
covered change; requesting independent review needs an eligible reviewer.
Explain the consequence in ordinary language and adapt the choice to the
project. Zero required approvals can be a usable sole-maintainer choice.

Honor informed unconventional choices and intentional freezes. Distinguish
them from accidental deadlocks using the user's stated intent and actual
actor/check availability. When the difference matters and is unresolved, ask
the intent question before applying the contested control. Cite the actual
applicable policy when it constrains a choice. For concrete active harm, such
as executing untrusted code with privileged CI credentials, explain the
mechanism and prepare a safe alternative. Do not invent a policy from a
preferred default or turn every operational inconvenience into a prohibition.

For hardening, identify the project's languages, layout, build requirements,
non-code contracts, threat concern, and trust boundaries. Select useful
analysis and validation before choosing gates. Demonstrate separately that
analysis runs, covers relevant content, and is enforced for the intended actor
and change. CodeQL does not replace content validators or ordinary tests, and
a successful workflow does not prove a merge gate. Keep spend within the
user's selected boundary using actual owner allowance and controls.

## Apply and establish the result

Follow [application and verification](references/apply-and-verify.md). Use the
existing maintained writer and supported native tools; research an unfamiliar
authorized setting rather than rejecting it because it is absent from these
guides. Preserve unrelated state and distinguish a verified no-op, a changed
setting, unavailable permission, inherited enforcement, and unknown effect.

Invoke `versionkeeping:checkpointing-and-publishing-git-work` for
`operation:git-ref-push` when maintained source needs Git
checkpoints/publication. Invoke
`mergecraft:publishing-reviewable-prs` when that change needs PR creation or
canonical PR text/readiness publication (`operation:publication-evidence`),
under its own contract. Use `tricritical:loop` for `operation:review-loop`
when applicable policy or the task requires independent
review and revision. A hosted-only setting change need not manufacture a Git
commit or PR. Respect the existing owners of ordinary review, publication,
relations, and merge actuation.

Reobserve before dependent effects. A change to rules, merge methods, check
identity, events, or permissions can invalidate a caller's cached readiness or
relation assumptions. Return the changed premises and evidence to that caller
so it can reassess through its owner; never carry an old readiness verdict
forward solely because the setting write succeeded.

Report what was observed and applied, what behavior was demonstrated, and
what remains unavailable or uncertain. Separate source validation, settings
readback, actual CI coverage, and causal enforcement evidence. Retain enough
non-sensitive evidence for the next invocation to recover the procedure and
its limits; renew conclusions when their material inputs change.
