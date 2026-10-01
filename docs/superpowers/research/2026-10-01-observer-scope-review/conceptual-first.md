> Frozen first-round report. Later corrections and coverage limits are recorded in the follow-up and synthesis; this report is retained as research history.

# First-round conceptual design: notifying a Claude Desktop-hosted Code task

## Finding

The smallest credible path is a native, task-addressed delivery surface, **if** one exists and exposes receiver-side evidence. It would need to address the existing Claude Desktop-hosted Code task by a stable identity, check its purpose-scoped consent immediately before sending, and return or permit retrieval of a receipt and acknowledgment produced on that task’s side. Neither the existence nor the semantics of such a surface has been checked in this lane.

If native delivery cannot provide those properties, the next plausible path is a receiver-cooperating bridge. A local mailbox alone can store text, a link, and a correlation ID, but it cannot prove that the intended task received them. A bridge needs a task-bound receiver component that records delivery and emits a correlated acknowledgment. That adds lifecycle, identity, and observation machinery. Sender-side submission, a changed transcript file, or a desktop notification cannot close the receipt gap.

No route is qualified. This is a conceptual first pass based on the supplied contract. It contains no public-source finding, product capability claim, or runtime observation.

## Contract to test

The destination is one exact, existing, user-owned Code task hosted by Claude Desktop on the same Linux machine. The sender is ChatGPT in Codex mode. The notification is informational: short text, a reviewable context link, and a correlation ID. Acknowledgment proves receipt only. It does not accept work or authorize the receiver to act.

Several checks belong at different points in the protocol:

- **Before submission:** bind a stable peer identity to the stated purpose and consent; freshly confirm that the binding still names the intended task. A matching title, recent activity, or a saved task ID without a current check is insufficient.
- **At delivery:** obtain evidence originating from the bound receiver, then an explicit acknowledgment that names the correlation ID. A sender API reporting “submitted” proves only that it accepted a request.
- **Across delivery:** preserve the effective account route, active model, applied permission mode and rules, grants and pending changes, and worktree and current directory. Saved configuration may describe intent while the running task uses different effective values.
- **After uncertainty:** if submission may have happened, reconcile against receiver evidence before any resend. Keep “held,” “refused,” and “outcome unknown” separate. None triggers an automatic retry.

A useful minimal record would bind purpose, receiver task identity, correlation ID, content digest, and submission attempt. The receiver evidence would name that binding through a channel the sender cannot fabricate. Acknowledgment can be a second receiver event or a distinct field in an authenticated receiver event, provided its meaning is explicit. Reusing the correlation ID for an uncertain resend risks duplicate delivery; an attempt ID can distinguish transport attempts while preserving one logical notification. This is a proposed shape, not an accepted protocol change.

“Reviewable link” also needs a concrete test. The receiver must be able to open the intended context with its actual account and permissions, and the link must identify the context rather than merely open an application. A link’s presence in the payload does not prove reviewability.

## Candidate families

| Candidate | Possible full-contract fit | Missing fact and cheapest discriminating check | Cost and principal failure |
|---|---|---|---|
| **Native task-addressed message or queue** in the Claude Desktop host, callable from Codex through a supported interface | **Conditional; best fit if available.** Host-managed identity and task-local delivery could reduce custom machinery. | Inspect first-party API and source for addressing an existing Desktop-hosted Code task, task-side delivery events, acknowledgment semantics, and effective-state introspection. | Low operational cost if all are native; otherwise a submission receipt may be mistaken for task receipt, or a send may resume the task under changed settings. |
| **Native host extension or task event hook** that receives an addressed message and acknowledges from the task boundary | **Conditional.** It could provide the receiver witness while retaining host ownership of task identity. | Check official extension and hook contracts for idle and busy delivery, task identity, lifecycle, and whether hooks can observe effective route, model, permissions, and directory. | Medium build and maintenance cost; hooks may run only at selected events, never on an idle task, or outside the task’s effective context. |
| **Receiver-cooperating local bridge** with per-task registration, mailbox, and task-side acknowledgment | **Conditional.** It can be designed to express every state, but qualification depends on a reliable task-bound receiver. | First establish a supported way for the exact task to register, receive while idle or busy, and emit evidence. A small disposable-peer proof would then distinguish this from a host-only mailbox. | High lifecycle and interruption cost; stale registration, a dead receiver, an acknowledgment by the bridge instead of the task, or registration to the wrong task. |
| **Shared MCP resource or tool polled by the receiver** | **Conditional only if polling is a supported, reliable part of the existing task’s lifecycle.** | Check whether the Desktop-hosted task autonomously polls while idle and at safe points while busy, and whether a tool response is incorporated into that same task. | Medium cost; an idle task may never poll, a busy task may delay indefinitely, and a tool call may show access without proving notification delivery. |
| **Native composer or UI automation aimed at the exact task** | **Possible in principle, weak first choice.** It still needs receiver evidence and live state checks. | Check whether the UI exposes stable task identity, pending changes, applied controls, and a task-origin acknowledgment without relying on visual inference. | High interruption and maintenance cost; focus can drift, a draft may remain unsent, the wrong task may receive text, or a busy turn may be disturbed. |
| **CLI resume or session attachment from a new process** | **Unclear and likely a different execution route unless proven otherwise.** | Check first-party semantics: does attachment address the existing Desktop-hosted task and preserve its effective account, model, permissions, and cwd, or start another process/session? | Medium to high cost; duplicate task identity, implicit overrides, or a changed working context. |
| **Transcript, profile, or session-file mutation** | **Not credible without a supported receiver contract.** It is also outside this research lane. | A first-party specification would have to establish live ingestion, identity, safe concurrency, and receipt evidence. | High corruption and compatibility risk; disk bytes can change while the running task receives nothing. |
| **Human desktop notification or deep link** | **Contract change.** It notifies the operator, not the Code task; human acknowledgment is not task receipt. | No product search is needed to establish this semantic difference. | Low build cost, but it depends on human forwarding and cannot satisfy receiver-origin evidence. |

The native options could collapse into one implementation if the host already supplies a task-specific mailbox and task-side event stream. Conversely, an API that only creates a new task, posts to a generic conversation, or reports that a host queue accepted bytes is insufficient. Product names and familiar interaction patterns do not establish these capabilities.

## What needs proof

**Structural guarantees** should come from the selected mechanism: a stable destination identifier, a purpose-and-consent binding, a receiver-origin evidence channel, an acknowledgment format that includes the correlation ID, and an idempotent or reconcilable submission record. The sender must not be able to manufacture the receiver event simply by writing to its own ledger.

**Source qualification** must establish what “existing task” means for each interface, where a send is admitted, and when the task can observe it. It must also establish whether a send can implicitly resume or reconfigure the task. If documentation describes only a saved model or permission setting, that does not answer which account route, model, rules, grants, pending changes, worktree, and cwd the live task actually uses.

**A live experiment** would then test behavior on purpose-created disposable idle and busy peers. A successful idle delivery tests basic addressing, receipt, acknowledgment, link access, and effective-state preservation. A busy delivery tests whether notification waits for a safe point and whether the existing context continues coherently. Busy continuity is diagnostic; an acknowledgment alone cannot establish that uninterrupted continuation occurred. Synthetic failures should include stale consent, wrong peer, receiver refusal, lost acknowledgment, ambiguous submission, duplicate correlation, delayed busy delivery, and changed effective state. The experiment must record receiver-origin events independently of the sender’s success report.

An ambiguous attempt should remain unresolved until the receiver evidence can be queried. If no receiver query or durable event exists, the system must expose an unknown outcome and hold the resend. Calling a timeout “not delivered” would invent evidence. A refused notification should retain its explicit refusal and correlation; a held notification should retain why it has not advanced. Neither is a retry instruction.

A new application build should enter the unassessed state. The cheapest check is whether its source-backed interface and event meanings remain compatible, followed by a small disposable-peer smoke test, then the relevant failure checks when semantics may have changed. Version change alone does not prove incompatibility; an old proof alone does not qualify a changed build.

## Requirements worth clarifying without silently changing them

“Receiver-origin delivery evidence” could mean a task-local event emitted before the model sees the notification, or evidence that the running task incorporated it into its context. Those are different claims. The required explicit acknowledgment suggests the second step must be observable, but the accepted contract does not specify whether the task host or the model emits it. This decision affects the smallest viable native API. It should be put to the operator if source and experiments leave both interpretations viable.

The preservation requirement may be satisfiable by a non-interfering transport plus live before-and-after observation. It should not be weakened to comparing saved metadata. If a platform exposes no authoritative live view of account route or applied permission state, that remains a qualification gap rather than an inferred pass. The same applies to grants and pending changes: absence from a UI view is not evidence that none exist.

Same-machine placement lowers transport complexity but does not establish task identity or consent. Purpose-scoped consent should be bound to the exact peer, then freshly checked; it should not be inferred from an old task, a similar title, or the operator’s general ownership. The initial proof’s disposable peers avoid treating historical tasks as experimental material. Applying a qualified route to a later, real peer would still require that peer’s own consent and fresh check.

If the operator chooses human-mediated notification, a generic host queue acknowledgment, or a new-task handoff, those could be useful workflows. Each changes this contract and should be labeled and decided as such. Security acceptance, permission redesign, and containment policy are outside this design pass.

## Ranked investigation order

1. **Search first-party surfaces for exact-task native delivery.** The fastest disconfirmation is an API that addresses only new sessions or generic conversations, has no task-side receipt, or silently changes execution settings. If a full native surface exists, avoid building a bridge.
2. **Check task-host event and extension contracts.** Look for a receiver callback on the same task while idle and at safe busy boundaries, plus task identity and effective-state observation. If callbacks are only process-global or turn-start hooks, test whether they can meet the exact-peer and idle-delivery contract before designing around them.
3. **Check supported receiver cooperation through MCP or equivalent tools.** Establish whether a task can receive without a user prompt or model-initiated poll. A resource the model *could* read is not a notification path.
4. **Only then sketch a local bridge against the supported receiver boundary.** Minimize it to registration, one addressed payload, receiver event, acknowledgment, and reconciliation query. Do not build a queueing service before proving the receiver can witness delivery.
5. **Use UI or CLI routes as fallback research.** They may offer an early demonstration, but they carry larger identity, interruption, and maintenance questions. Disconfirm any route that creates a separate task or cannot expose effective state.

## Exposure and evidence inventory

A later implementation would handle the destination task identifier, purpose and consent record, short text, context link, correlation and attempt IDs, delivery events, acknowledgments, and effective-state observations. Depending on the route, these could appear in a host API, local bridge storage, operating-system IPC, MCP logs, application UI, or vendor-synced task history. The link might grant access, reveal a title or workspace, or fail under the receiver’s account. None of those exposures was inspected here. The design should inventory them against the selected route before an operator accepts it; this report does not make a security acceptance decision.

**Source and search log:** I read the coordinator-supplied `conceptual/r1/brief.txt`, the applicable repository instructions supplied in the task prompt, and the installed `research` skill at the installed `research` skill. Two catalog-derived plugin paths for that skill did not exist; a filename search over the installed skill roots located the latter file. The skill normally calls for delegation and a written report, while this frozen assignment expressly forbids delegation and writes, so I performed the analysis locally and return it here. I did not read project source or history, peer work, memory, private task data, public documentation, or external solutions. No app or runtime action was performed.
