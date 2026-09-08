# Daybreak Routing Capability Reference

This reference selects a model-routing disposition for cybersecurity-related and cybersecurity-adjacent work. It does not decide whether to delegate, create tasks, mutate trackers, or perform actions. The owning delegating workflow retains action authority and topology.

Treat cybersecurity-related and cybersecurity-adjacent whole tasks and bounded subtasks as Daybreak-routed work. This policy overrides the general model matrix and fallback rules for that scope.

In ChatGPT or Codex harnesses authenticated with an OpenAI account, route that work to a Daybreak model whenever any permitted Daybreak route is genuinely runnable. In every other harness, prefer a Daybreak model whenever any permitted Daybreak route is genuinely runnable. The Daybreak model executes the cybersecurity work; it does not merely choose a model for another agent. These rules do not govern unrelated work.

Classify the current bounded scope against the same cybersecurity criteria immediately before every concrete delegation, including initial creation, reuse, resume, follow-up with the same agent, and each review cycle. Prior Daybreak assignment, agent identity, or continuation does not carry the classification forward. Use the general matrix when a new bounded scope is unrelated, even inside an existing Daybreak task. Keep a resumed cybersecurity-related or cybersecurity-adjacent scope Daybreak-routed. Never relabel or narrow scope to avoid these guardrails.

When a security-relevant dependency or other evidence dependency changes enough to invalidate an earlier review, review the whole changed security-relevant scope supported by that invalidated evidence. A review of only the dependency delta does not preserve the earlier pass.

Inventory these routes independently before selection:

1. A Daybreak model in the native subagent selector.
2. A Daybreak model in the peer or sibling task selector.
3. Every Codex session-launch surface available to the harness, expanded across every authenticated account home allowed by the operator's permitted private account-binding catalog (`~/.agents/daybreak-account-bindings.md` for Codex account-home routes), including cross-harness Codex invocation.

A route is one invocation surface plus the account home, authenticated identity, model, and capability state required by that surface. Catalog entries are inputs, not routes. Inventory cross-harness Codex invocation before declaring Daybreak unavailable. Read the permitted private catalog before using an account-home route. If it is absent, unreadable, or does not match the authenticated identity, treat that route as unavailable. Never disclose its entries or infer a binding from a directory name.

A no-task-data local status refresh may refresh only authentication, selector exposure, entitlement, capacity, the exact exposed model, and model-runnability. It is read-only and may make only the route's status request needed to observe those facts. It must not create a task session, transfer task data, use task workspace or task tools, perform an external side effect, delegate, or execute work. Run this refresh automatically whenever a permitted account route needs a missing or stale observation. It requires no operator prompt because it sends no task data and performs no work.

The status refresh is distinct from the separate harmless runnability probe. The harmless probe contains no task data and may run only when existing task or workflow authority covers its route, account, workspace, tools, and applicable actions. A status refresh never satisfies or consumes that probe.

During an authorized status refresh, route metadata exposed for unrelated tasks may be observed without reading their task data. An existing task is eligible for execution only when delegation created it for the current source task and bounded purpose or the operator identified it as a same-purpose companion. Never reuse an unrelated task as an execution or authorization route, including its model, account, entitlement, permissions, or context.

A route is genuinely runnable for delegated or executed task work only when existing task or workflow authority covers the account, data boundary, workspace, tools, harmless probe, and applicable external actions; any itemized transfer approval required below is in force before task data is sent; the current status confirms the exact Daybreak selector, matching authenticated account, and remaining capacity; and the harmless no-task-data probe succeeds.

Existing task or workflow authorization covers ordinary route setup, the harmless probe, and handoff of data that is not sensitive, secret, or uniquely proprietary when each stays within the authorized account, data, workspace, tool, and action scope. Do not request separate Daybreak-specific permission for that ordinary work. This does not expand scope, authorize consequential actions, or override explicit prohibitions. The owning workflow remains responsible for any separate consequential-action permission.

Before sending a payload containing sensitive, secret, or uniquely proprietary data, obtain explicit approval to transfer those items to the selected route. Identify every such item by safe description and location, never by exposing contents or secret values in the request. Reuse an existing approval without another prompt only while it remains valid for the exact items, selected route and account, data boundary, workspace, tools, action scope, and bounded purpose. Reuse never waives classification before the next delegation event.

Picker visibility, selectability, authentication, capacity, session start, and successful execution are separate facts. Status and incidental route metadata establish facts but create no task-data, workspace, tool, action, delegation, or execution authority. Neither status nor the harmless probe implies protected-data transfer approval. Resolve the exact model currently exposed; never invent a slug or reuse a stale one.

If authority for the account, workspace, tools, probe, or applicable actions is absent, classify the route as unavailable without running the harmless probe; the automatic no-task-data refresh remains permitted. If only itemized protected-data approval is absent, an otherwise authorized harmless probe may run, but task-data handoff remains blocked.

Record a timestamped, redacted status and a declared freshness window for each exact invocation-surface, account-binding, authenticated-identity, model, and capability-state tuple. Reuse it only inside that window while the full tuple is unchanged. A dated catalog observation is historical, not current by default.

Invalidate the observation when the tuple, selector, entitlement, capacity, authentication, data boundary, workspace, tool scope, external-action scope, or freshness window changes. The changed tuple receives one new no-task-data refresh and, separately, one harmless probe when route and probe authority covers it. Permit only one of each operation per exact tuple per freshness window. Neither creates task-work authority or protected-data transfer approval.

Local/private operational state may use account IDs, account-home identifiers, or safe stable local labels to distinguish permitted accounts. Scrub account IDs, account-home identifiers, stable labels, and derived home or path names before any nonlocal or public persistence or transmission. Use only a generic non-stable marker or redacted status there. Never expose credentials, tokens, decrypted secrets, catalog entries, or unrelated task data outside the narrow local operation that requires them.

When no permitted Daybreak route is genuinely runnable, record why each route failed and select one disposition:

- In ChatGPT or Codex with an OpenAI login, local non-Daybreak fall-through is forbidden. Defer until capacity returns when exhaustion is the blocker, use another available harness whose model policy may select an operator-approved next-best candidate, or create a tracker ticket when authorized. An approved model does not establish missing delegation authority.
- In every other harness, including ChatGPT or Codex without an OpenAI login, the same dispositions are available, and the current harness may fall through locally under its normal model policy.

Before returning an executable cross-harness disposition, the owning workflow must verify that existing authority covers the target harness and account, data boundary, workspace, tools, and external actions, and obtain only missing authority. Existing in-scope authorization is sufficient for ordinary work; protected payloads require the itemized gate above. Transfer no task data while authority remains incomplete.

Deadline, sunk cost, and convenience do not permit forbidden local fall-through. If no authorized disposition can proceed, return a narrowly scoped handoff to the owning workflow.

For root-only work, when the native route cannot run Daybreak but a permitted peer, sibling, or cross-harness Daybreak route is genuinely runnable, return that route and the bounded Daybreak scope to the owning workflow. The workflow must create the dedicated peer or sibling task before execution; a direct cross-harness session does not bypass that boundary. Keep integration and non-security coordination in the original task.
