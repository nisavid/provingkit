# Desktop Code to an independent Codex GUI peer: first source design

Queue and the owning App Server remain useful notification candidates. Neither is a qualified Claude Desktop caller route to an independently opened ChatGPT Codex GUI peer. The packet establishes queue admission, conditional idle dispatch, local owner rejoin, and inspection mechanisms; it does not establish the actual Desktop caller interface, GUI owner/server/store/connection association, or independent correlated receiver receipt.

This is the frozen first investigation for issue 561, before sibling exchange. I used `research`, `domain-modeling`, `prototype`, and `capturing-agent-procedures` under the request's report-only restriction. I propose seams; I implemented no prototype or tests and executed no reviewed code, CLI, receiver operation, private read, authentication, installation, or external action.

## Evidence and claim boundary

All fifteen plan-bound input byte counts and SHA-256 identities matched before source examination and again afterward. The plan hash is `9f630100289fdef2922d3cc2475f9a49978ac424f30172c81bb97716c982a504`; selection hash is `9e204f640a9626deed03fd8c56a1f6df64d835f571be5d3776b8e7bc6589d031`; request hash is `2a3ae9b8dc4c9f51a397e1874d7d52b62a76cacfd9b9ce402aa0e335633c1834`. Their frozen bindings matched.

Current public source is commit `97239fd052db455bd08c41afcdab738e0fe83b87`. The supplied complete primary-source packet totals 394,722 bytes. I examined its CLI entry, queue registration/processor/service, writer, README, directory inventory, and the thread processor's method inventory and relevant ownership, resume, and inspection bodies. This is a focused source investigation, not an exhaustive code review. The commit does not identify an installed GUI build.

Source keys below link to the examined immutable files:

- **C:** [CLI queue entry](https://github.com/openai/codex/blob/97239fd052db455bd08c41afcdab738e0fe83b87/codex-rs/cli/src/queue_cmd.rs).
- **Q:** [Queue request processor](https://github.com/openai/codex/blob/97239fd052db455bd08c41afcdab738e0fe83b87/codex-rs/app-server/src/request_processors/thread_queue_processor.rs).
- **S:** [Queue service](https://github.com/openai/codex/blob/97239fd052db455bd08c41afcdab738e0fe83b87/codex-rs/ext/queue/src/service.rs), with [registration](https://github.com/openai/codex/blob/97239fd052db455bd08c41afcdab738e0fe83b87/codex-rs/ext/queue/src/lib.rs).
- **T:** [Thread processor](https://github.com/openai/codex/blob/97239fd052db455bd08c41afcdab738e0fe83b87/codex-rs/app-server/src/request_processors/thread_processor.rs).
- **W:** [Local live writer](https://github.com/openai/codex/blob/97239fd052db455bd08c41afcdab738e0fe83b87/codex-rs/thread-store/src/local/live_writer.rs).
- **R:** [App Server README](https://github.com/openai/codex/blob/97239fd052db455bd08c41afcdab738e0fe83b87/codex-rs/app-server/README.md).

The frozen reviewed comparison at `61b99e73` and OpenAI correction retain older `092d3acd` evidence. I retain their conclusions with their revisions, including the active-turn-ID steering contract and Python ExternalMessage distinction. Missing current implementations prevent promoting those details into a complete current wire contract. The accepted operation decision and confirmed cohort govern the older comparison's pending-decision language.

## Interfaces and evidence

| Candidate interface | Source-supported behavior and inputs | Binding and evidence still required |
| --- | --- | --- |
| CLI queue | C exposes `--thread` (UUID or exact session name), nonempty `--message`, remote options, and configuration overrides; rejects image attachments. It delegates to `codex_tui::run_session_queue_command` and returns a string. | Missing TUI delegation prevents identifying its store/server selection, name resolution, authentication, output meaning, and correlation mapping. Desktop-hosted Code execution/plugin/tool exposure is independently unknown. Prefer supplied native UUID over a name; require resolved-ID equality. |
| App Server queue admission | Q `add` uses thread ID, input, and client user-message ID; responds with queue ID, input, and client ID. Eligible stored ordinary threads need not be loaded. The loaded branch checks ephemeral status; the stored-thread fallback refuses archived records; unloaded spawned subagents and disallowed loaded V2 children are refused. Service availability is conditional. | Current protocol definitions, actual callable owner/store, caller access, provider/config policy, receipt reader, and consent. Queue storage is admission evidence. |
| App Server queue start | Q `start` requires loaded thread and checks its model provider. Optional queue ID selects an item; absent ID can select the first item. Started response contains turn/root-turn IDs and in-progress status with items not loaded. Busy/pending turns are rejected; draining is distinct. | Bind the selected queue ID and resulting native turn. Turn start establishes neither receipt nor ACK. Existing queue entries and automatic dispatch complicate attribution. |
| Owning App Server turns | Frozen research nominates `turn/start`, active-ID `turn/steer`, and external tool-content input. R names provider checks for turn start/steer and describes settings effects. | Current turn implementation and full schema are absent. This packet cannot finalize their current idle/busy rejection, message correlation, ExternalMessage mapping, or transport/access contract. |
| Receiver inspection | T exposes loaded-ID listing, `thread/read`, turn pagination, and item list/read. Loaded list uses this server's manager; persisted and live reads differ. Item anchors require their turn and history scope; paging may be unsupported. | An independent permitted observation of the exact GUI-owned native thread, complete relevant pages, timestamps, correlation, and reader limits. Sender response or sender-produced trace is insufficient. Some paginated loaded-history reads call persistence; a proposed reader must disclose that footprint. |
| Owner rejoin/continuation | T `resume_running_thread` searches this server's manager, validates requested path, and attaches a listener. Cold resume uses stored history and configuration; W acquires a writer lock before resuming. | Prove this server owns the GUI thread. A newly launched SDK/server and valid stored ID do not supply that association. Current writer-lock implementation and namespace binding remain missing; W alone does not establish cross-process exclusion. |

Queue methods live in Q and S, not directly in T. The retained 404 for `codex-rs/ext/queue/src/cli.rs` remains evidence; the bounded supplied CLI directory nominated C. It was not silently replaced with an inferred CLI implementation.

## Profiles and ownership

Define a route binding as: declared caller surface/build and available actuator; exact GUI chat reference and native thread mapping; GUI execution host; owning server instance and transport connection; configured thread/queue store namespace; installed component versions; eligibility; and independently observed state. Every field needs a source and observation time. “Loaded” always means loaded in the addressed manager. No public CLI source supplies the actual GUI association.

**Loaded idle, direct owner:** S enqueue stores the input, emits queue change, and calls `wake_if_loaded`. Its idle contributor attempts `start_turn_if_idle`, and successful start deletes that queue entry. Eligibility, installed extension, current policy, and receiver observation remain conditions. Enqueue can trigger existing queued work ahead of this message.

**Loaded busy:** enqueue can remain durable while the active turn runs; the idle contributor supplies a subsequent dispatch mechanism. Manual queue start refuses active/pending work. This is queued user input, not demonstrated between-tool-call peer delivery. Steering is a separate candidate requiring its current implementation and active-turn binding. No latency or uninterrupted-context claim follows.

**Shared store with another owner:** S checks SQLite change version on a source-configured ten-second interval, uses a revision index restricted to this manager's loaded IDs, and considers newly loaded/resumed threads. Its watcher skips Running, Interrupted, Shutdown, and NotFound statuses. Shared storage plus an operating compatible owner watcher can therefore contribute a route without direct caller attachment. Store sharing, watcher installation/activity, and GUI ownership were not observed. Ten seconds is configuration, not measured delivery latency.

**Unloaded:** Q can admit an eligible stored ordinary thread. S does not load absent owners; manual start says resume first. A later loading/resume mechanism can discover queued work, but its trigger and authority require separate evidence. Unloaded, interrupted, and restarted conditions must remain separately recorded.

**Resume:** T can shut down and cold-resume a loaded idle cache entry with no subscribers when overrides differ and shutdown completes. Observable loaded threads, protected children, or incomplete shutdown retain rejoin behavior and ignore overrides. Cold loading can restore or change configuration and invoke idle work. “Resume for inspection” is therefore not a generally inert setup action or automatic settings-preservation guarantee.

R's experimental `readState` “receipt” tracks read/unread completed results. It is unavailable for product-owned/service threads and is not correlation-bearing notification receipt or explicit ACK. Its presence or absence cannot qualify this GUI operation.

## Input, consent, and outcome contract

Q converts input to `TurnInput::UserInput`; S accepts only user input and generates a client ID when absent. Peer labels must disclose those semantics. They authenticate neither sender nor operator authority. The older ExternalMessage contract uses lower-priority external tool content; it also does not authenticate a peer and is not interchangeable with queue input.

A proposed envelope carries operation ID, inert correlation token, disclosed sender surface, exact target, purpose, requested receipt/optional ACK, and references to verified original grants. Metadata and message text cannot create a grant. Preserve applicable original/transitive task-and-purpose consent and identify verification or receiver-policy gaps. The present source/synthetic grant authorizes no live send or private setup. Terminal plugin capabilities cannot be imported into the Desktop caller.

For this lane, notification requires independent correlated receiver-side receipt. Explicit ACK is a separately qualified stage. Retain the separate issue 212 Desktop route's receipt-plus-ACK and stronger preservation requirements; this weaker profile does not replace them.

The evidence chain should retain request ID, client-message ID, queue ID, native thread, turn/root-turn, receiver item/event, payload correlation, observation source/time/completeness, and any ACK naming that correlation. Current protocol/core propagation of these IDs still needs source examination. The code inspected supplies no demonstrated idempotency contract for client IDs.

Record admission, queued/held, start, receipt, ACK, and completion separately. Queue disappearance can mean successful start, explicit deletion, or discarded malformed/non-user payload; it is not receipt. S can start a turn before deletion fails, so an error can coexist with submission. Missing response or timeout remains unknown for the affected stage. Reconcile queue/history/owner evidence before resend; empty queue or absent transcript evidence alone does not prove non-submission. Only proved pre-submission transient failure admits a bounded retry under existing consent. Held/refused outcomes do not trigger automatic resend.

The six-operation target stays visible: queue contributes notification/request submission and queue inspection, but no creation or independent reverse inbox. App Server exposes thread creation/resume/fork and status/history mechanisms, while qualified fulfillment, creation observation, later reply, and continuation-context evidence remain separate. A receiver completion claim needs caller validation for work. Same native task continuation needs requested/resolved IDs and prior-context evidence; a fork or replacement is separately reported.

## Exact source gaps and later test seams

No additional sources were acquired. At the same public commit, request these missing paths next:

1. `codex-rs/app-server/src/request_processors/turn_processor.rs` and `thread_input.rs`: current turn start/steer/tool-output behavior, direct-input eligibility, correlation, and policy gates. Q explicitly imports these modules.
2. `codex-rs/tui/src/lib.rs`: nominated entry to trace `run_session_queue_command` and its re-export/owning module. This location is a proposed acquisition path, not verified implementation ownership. Acquire the exact delegated module after that trace.
3. `codex-rs/cli/src/lib.rs`: directory-confirmed missing source for CLI wiring, remote endpoint/config helpers, and queue exposure.
4. `codex-rs/app-server-protocol/src/protocol/v2.rs`: nominated schema path for exact queue/turn/read/resume wire types; confirm layout and any split schema files before reliance.
5. `codex-rs/rollout/src/writer_lock.rs`: current lock implementation to complement W's call sites. The older correction's lock source remains older evidence.

Also missing are dispatcher/initialization/transport-auth ownership, extension installation, QueueStore implementation, and core start-if-idle/lifecycle semantics. Their exact current owning files require bounded directory/module tracing; this packet does not justify inventing their paths. Public source cannot fill the separate live gaps: actual Desktop tools/shell, target-native mapping, GUI build/owner/connection/store, available reader, auth scope, policy, watcher activity, or costs.

The smallest useful later source/synthetic boundary agreement is:

| Proposed seam | Cases that answer an uncertainty | Evidence limit |
| --- | --- | --- |
| Binding and correlation validator | Wrong caller, name resolving elsewhere, wrong server/store, stale turn, wrapper/native mismatch; same binding with matching receipt and separate ACK. | Invented declarations/observations only; no actual GUI association. |
| Outcome trace classifier | Admission-only, start-only, unrelated receipt, matching receipt without ACK, queue disappearance, start-then-delete-error, lost response, held/refused, proved pre-submission failure. | Tests the declared evidence contract and unknown-send handling, not delivery. |
| Queue boundary with fake store/manager | Loaded idle versus busy/unloaded/interrupted; existing head item; watcher revision/new-load discovery; stored archive refusal, loaded ephemeral checks, and spawned-child eligibility; concurrent selection/deletion. | Constructed mechanism cases after public dependencies are pinned; no deployed watcher or failure-recovery claim. |
| Current turn/TUI contract adapter | Exact-ID selection, owner versus newly launched server, idle start versus busy steer, transport/auth setup effects, ID propagation. | Blocked on missing source/schema; no terminal-to-Desktop capability transfer. |

Agree on these externally meaningful assertions before implementation, then use `tdd` for low-level work. A later throwaway logic prototype can display independent binding, queue, turn, receipt, ACK, and unknown states using invented traces. Receiver interpretation/ACK compliance requires a separate behavioral eval; exact-target delivery requires separately granted live evidence.

## Procedure reconciliation and effort

For the common comparison/reaction join in 569, preserve this producer revision, source pins, directional caller gaps, three queue profiles, user/tool semantics, original-consent references, independent receipt/ACK rules, uncertain-send reconciliation, proposed seams, and explicit costs. Load and record the reviewed `updating-cross-harness-catalog` revision from 552 when available. Reconcile coherent records and generated views through that procedure while preserving concurrent work; send useful method corrections to the existing workflow producer. I made no catalog, procedure, tracker, installation, or publication update.

Actual work was one bounded source-research worker, local frozen-file reading and identity hashing, with zero new public-source acquisition and zero receiver/provider experiments. Selection requested `gpt-6.1-sol/high`; the selection record does not attest the product build, executed model, or permissions. Research billing, token totals, measured wall/CPU effort, and runtime costs are unavailable. Later costs include caller access preparation, transport/auth setup, owner/store binding, independent permitted history acquisition, receiver turns, waiting, interference, and restoration.

The next bounded check is acquisition and examination of the missing turn and TUI delegation sources. Fixture setup, meaningful synthetic implementation, live operation grants, and final independent review remain later work. Task Witness stays deferred.