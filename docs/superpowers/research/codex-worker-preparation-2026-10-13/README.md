# Controller-created Codex worker preparations

These two independently frozen source designs compare direct Codex CLI execution, the Python SDK’s owned App Server, and ACPX with a Codex adapter. They retain each caller’s access and runtime-binding requirements separately.

- [ChatGPT to created Codex workers](chatgpt-to-created-codex-workers.md) traces the receiver mechanisms, requested versus applied settings, task addressability, returned-output checks, and one same-native-task context-marker design.
- [Claude Desktop to created Codex workers](desktop-to-created-codex-workers.md) gives the same receiver candidates conditional Desktop command and external MCP entrances. Generic SDK declarations establish no actual Desktop tool exposure.

The reports separate ACPX’s preferred installed-package resolution, its `^1.1.5` package-execution fallback, and explicit adapter selection. Installed resolution does not enforce the fallback range; actual executable identity remains unproved. Native task, wrapper, request, and turn identities remain distinct; a fresh fallback is a replacement. Neither report supplies a live caller connection, independent task readback, applied no-edit policy, validated runtime result, or continuation proof. They propose pure evidence models and tests; no such prototype was implemented in this increment.

[Compare the first cohort prototypes and record the operator reaction](https://github.com/nisavid/provingkit/issues/569) owns the combined comparison, catalog reconciliation, and actual reaction. Use [updating-cross-harness-catalog at its reviewed source revision](https://github.com/nisavid/provingkit/blob/701af706a0b2d70a9161742453bfc7c99aab952c/.agents/skills/updating-cross-harness-catalog/SKILL.md) when integrating the coherent batch. Initial source publication establishes no catalog update or live grant. The separately recorded Codex CLI-to-CLI lifecycle is a proposed same-harness control, not a cross-harness result.
