---
name: delegating-cross-agent-work
description: Use when choosing delegation, worker topology, authority, or execution handoffs.
---

# Delegating Cross-Agent Work

## Scope

Coordinators assign, track, and verify. Workers execute. Delegate bounded parallel, specialist, or waiting work.

Own target, topology, authority, execution handoffs, assurance, and integration.
Apply the [message/execution boundary](../choosing-agent-models/references/capability-probes-and-fallbacks.md#distinguish-messages-from-execution-assignments) first;
[choosing-agent-models](../choosing-agent-models/SKILL.md) owns model/effort selection.

## Choose the Worker Contract

Choose independently:

- target: exact family, surface, version, and executor;
- relationship: `child`, `peer`, or `external`;
- ownership: `leader-owned` or `user-owned`;
- transport: `native-tool`, `task-api`, `cli`, `app-server`, or `remote-api`; and
- required assurance: `product-attested`, `controller-observed`, or `self-reported`.

Choose leader-owned children for bounded work you create and end, leader-owned peers for independent sessions you control. Create or steer user-owned peers/tasks only with explicit consent. Cross product/control boundaries only when materially helpful.

Task identity and bounded purpose govern routing. Model availability never validates an unrelated task. Before non-native or separately owned probes, read [foreign-harness-peers.md](references/foreign-harness-peers.md).

## Kickoff

Record leader, repo, branch, immutable base, dirty state, submodules, and worktree. Check live state and policy; freeze topology and assurance minima before selection or edits. Reclassify scope and resolve model/effort through `choosing-agent-models` for each execution assignment or continuation.

Every thread, task, session, or subagent creation explicitly passes deliberately
selected model and effort wherever supported, including native Codex and Claude
Code Agent tools. Apply the
[field and continuation rules](../choosing-agent-models/references/capability-probes-and-fallbacks.md#pass-every-supported-selection-field)
for absent controls and continuations. Retain requests before inference;
global, desktop, and parent defaults never replace supported fields.

## Bounded Handoff

Bind each handoff's goal, success criteria, worktree, immutable base, facts, target behavior, scope, read/write and subdelegation authority, external-action authority, verification, output, and stop conditions. Recover and apply verified operator grants through [handoff authority](references/invocation-topology-receipt.md#handoff-authority). Preserve edits.

Read [scarce-specialist handoffs](references/scarce-specialist-handoffs.md) before assigning one.

For native Codex, select [Cloud or strict](references/native-codex-subagents.md).

Freeze ordinary review handoffs as `adapter:rolecasting-invocation-plan` under [invocation-topology-receipt.md](references/invocation-topology-receipt.md). Witnessed consumers also require `adapter:rolecasting-invocation-topology-receipt`. Model selection never supplies dispatch authority. Use [dispatch-evidence.md](references/dispatch-evidence.md) for witnessed execution and assurance.

Workers return one:

- `DONE`: complete and verified
- `DONE_WITH_CONCERNS`: complete with concrete concerns
- `NEEDS_CONTEXT`: name missing fact or decision
- `BLOCKED`: impossible within current scope, authority, or environment

Retry `NEEDS_CONTEXT` or `BLOCKED` only after input, authority, boundary, or capability changes.

## Batch and Wait

Batch small independent same-shape work into one dispatch and review its diff as one unit. Separate work needing its own judgment, own tests, or review surface.

Do local work before waiting, coordination only for coordinators. Avoid short polling; after bounded idle waits, reconcile live children and recover missed terminal results.

Use `surreal-intercom:communicating-with-agents` for peer communication and reconciliation.

## Leader Integration

- Keep parallel edit scopes disjoint.
- Record immutable base before edit-capable delegation; never infer `HEAD~1`.
- Review patches, claims, captures, logs, and summaries.
- Treat worker results as inputs, not decisions.
- Integrate in the owning worktree; verify the contract.
- Own consequential judgment, ambiguity, architecture, root cause, external actions, and message intent. Outside coordinating roles, write copy locally only if [qualified for it](../choosing-agent-models/references/general-tiers.md#published-text). Otherwise assign a qualified writer. Any authorized model may apply the writer's text verbatim.
