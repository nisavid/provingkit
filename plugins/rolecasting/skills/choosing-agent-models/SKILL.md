---
name: choosing-agent-models
description: Use when selecting a model or reasoning effort for an agent, subagent, Task, peer, or agent definition after delegation has been chosen.
---

# Choosing Agent Models

## Scope

Own model/effort selection and capability proof post-delegation. [delegating-cross-agent-work](../delegating-cross-agent-work/SKILL.md) owns family, surface, version, executor, relationship, ownership, transport, assurance, authority, handoffs, and integration. Model choice is a separate decision; it cannot repair topology or make an unrelated task a valid route.

Choose the lowest-cost model that preserves required judgment. Escalate for ambiguity, hard-to-reverse decisions, architecture, reviewer-facing work, or final integration.

Before every delegation or continuation, apply [Daybreak routing](references/daybreak-routing.md) to the current scope; use the general matrix for unrelated work.

## Preferred Codex Role Family

- **Astra** (`gpt-6-astra`): consequential judgment, unresolved architecture or diagnosis, final review, and integration
- **Astra low** (`gpt-6-astra`, `low`): defined, recoverable implementation, debugging, analysis, and review
- **Luna xhigh** (`gpt-5.6-luna`, `xhigh`): tightly specified, non-judgment legwork with cheap-to-repair mistakes

Luna is not a substitute for Astra on judgment work.

## Prove Target Capability

Use only a pair proven by both the target's live catalog and executor schema.
Reuse fresh, unchanged Daybreak observations under its routing rules.
Never infer executor support, invent a slug or effort, or treat selection as
invocation authority.

Read [capability-probes-and-fallbacks.md](references/capability-probes-and-fallbacks.md) only when selecting an explicit pair, handling an unavailable preference, using another harness, or evaluating Fable.

## Selection Matrix

- Use **Astra** for scope, architecture, root cause, readiness, or final integration.
- Use **Astra low** for precise implementation, recoverable debugging, focused review, or tests against a settled contract.
- Use **Luna xhigh** for exact extraction, rubric classification, monitoring, or clerical edits.

Default independent code, specification, architecture, and closeout reviewers
to **Astra high**. In Cursor, proven `cursor-grok-4.6-high` is also strong for
consequential review, especially for an authorized foreign-harness perspective.
Keep the same authority, evidence, and integration boundaries. Use a weaker
reviewer only with concrete contrary evidence.

Select for the hardest judgment; preserve each role's specified effort.

## Fallback And Authority Gates

Use the referenced fallback rules when the preferred role is unavailable. Report a material fallback when it changes confidence, cost, or speed.

Treat Claude Fable as unavailable unless a current proof is supplied. Model selection does not authorize a proof invocation; only the operator's explicit authorization for that exact invocation permits attempting one.
