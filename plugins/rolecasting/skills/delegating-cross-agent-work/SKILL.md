---
name: delegating-cross-agent-work
description: Use when choosing delegation, topology, authority, or handoffs. Select models through choosing-agent-models.
---

# Delegating Cross-Agent Work

## Scope

Keep consequential judgment, ambiguity, architecture, copy, and coordination local. Delegate bounded parallel, specialist, or waiting work.

[choosing-agent-models](../choosing-agent-models/SKILL.md) owns model and effort selection. This skill owns target, topology, authority, handoffs, assurance, and integration.

## Choose the Worker Contract

Choose each axis independently:

- target: exact family, surface, version, and executor;
- relationship: `child`, `peer`, or `external`;
- ownership: `leader-owned` or `user-owned`;
- transport: `native-tool`, `task-api`, `cli`, `app-server`, or `remote-api`; and
- required assurance: `product-attested`, `controller-observed`, or `self-reported`.

Keep axes independent. Use a leader-owned child for bounded work the leader creates and ends. A leader-owned peer keeps an independent leader-controlled session. User-owned peers or tasks require explicit consent to create or steer. Cross the product or control boundary only when materially helpful.

Task identity and bounded purpose are route gates: model availability never makes an unrelated task valid. Read [foreign-harness-peers.md](references/foreign-harness-peers.md) before probing a non-native or separately owned surface.

## Kickoff

Record leader, repository, branch, immutable base, dirty state, submodules, and owning worktree. Check live state and policy. Freeze topology and assurance minima before selection or edits. Before every dispatch or continuation, use `choosing-agent-models` to reclassify scope and resolve model/effort.

Every thread, task, session, or subagent creation explicitly passes deliberately
selected model and effort wherever supported, including native Codex and Claude
Code Agent tools. Apply the
[field and continuation rules](../choosing-agent-models/references/capability-probes-and-fallbacks.md#pass-every-supported-selection-field)
for absent controls and continuations. Retain requests before inference;
global, desktop, and parent defaults never replace supported fields.

## Bounded Handoff

Every prompt binds goal, success criteria, worktree, immutable base, facts, target behavior, scope, read/write and subdelegation authority, external-action authority, verification, output, and stop conditions. Recover and apply verified operator grants through [handoff authority](references/invocation-topology-receipt.md#handoff-authority). Preserve edits.

Read [scarce-specialist handoffs](references/scarce-specialist-handoffs.md) before assigning one.

For native Codex children, follow
[native-codex-subagents.md](references/native-codex-subagents.md).

Freeze ordinary handoffs as `adapter:rolecasting-invocation-plan` under [invocation-topology-receipt.md](references/invocation-topology-receipt.md). Witnessed consumers also require `adapter:rolecasting-invocation-topology-receipt`. Model selection never supplies dispatch authority. Use [dispatch-evidence.md](references/dispatch-evidence.md) for witnessed execution and assurance.

Workers return one status:

- `DONE`: complete and verified
- `DONE_WITH_CONCERNS`: complete with concrete concerns
- `NEEDS_CONTEXT`: a named fact or decision is missing
- `BLOCKED`: impossible within current scope, authority, or environment

On `NEEDS_CONTEXT` or `BLOCKED`, change the input, authority, boundary, or capability before retrying.

## Batch and Wait

Batch small independent same-shape work into one dispatch and review its diff as one unit. Separate work needing its own judgment, own tests, or review surface.

Do local work before waiting; avoid short polling, use a bounded wait when idle, then reconcile live children and recover missed terminal results.

For durable native Codex peer recovery, use [mailbox bookkeeping](references/native-codex-mailbox.md).

## Leader Integration

- Keep parallel edit scopes disjoint.
- Record immutable base before edit-capable delegation; never infer `HEAD~1`.
- Review patches, claims, captures, logs, and summaries.
- Treat worker results as inputs, not decisions.
- Integrate in the owning worktree; verify the contract.
- Retain authority for architecture, root cause, user-facing wording, and external actions.
