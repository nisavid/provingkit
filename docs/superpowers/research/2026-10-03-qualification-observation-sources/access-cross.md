# Access cross-examination: qualification endpoint state

The proposed Desktop adapter needs a separately reviewed Engine diagnostic producer to meet the accepted endpoint fields. It can bind an existing selected query and collect useful state, but the retained interfaces do not expose the complete applied account route, raw current Engine permission mode, or raw current cwd with failure provenance. This conclusion concerns source coverage. Loadability, fixture selection, and live qualification remain unproved.

## Frozen inputs and evidence boundary

- The access report is 31,763 UTF-8 bytes, including its final LF, with SHA-256 `67442a454c6078374304fb011afd5dc6a9147362521cb164a3706dc8a352380e`.
- The state report is 42,106 UTF-8 bytes, including its final LF, with SHA-256 `b9d5212f7ca31a01e10ebd33e77806ccd897284fea89110776c08863e4056456`.
- Both match `first-findings-manifest.json`. I reread the resolution and cross-examined the reports against the same retained-source allowlist. Neither report supplied authority.
- This pass used Research and Capturing Agent Procedures. It performed source reads only: no implementation, tests, file edits, private or live reads, vendor execution, query use, installation, publication, or tracker changes.

Anchors below are zero-based, end-exclusive byte ranges in the frozen artifacts already identified and hashed by the initial access report. `Manager` means `manager-pristine.js`; `SDK` means `sdk.mjs`; `Engine` means `claude.bin`. The repo source base remains `e971ae6fde6f4f4fa0b603e3a08bd0369b9481c6`. These sources establish possible code paths, not a running executor's identity.

## Reconciled facts and corrections

### Applied task model needs the relevant main-task context, not every internal context

The Engine's headless `get_settings` response obtains the current configured model through `st()` and exposes other model settings. The headless `set_model` path applies the accepted model through `xp(S)`, writes `mainLoopModelForSession`, and reports metadata. This is useful applied session evidence, beyond a saved Desktop choice. It remains distinct from observed fallback events. Engine `[221225050,221226960)` and `[221116660,221117650)` support this distinction.

The state report has a real additional concern: relevant context layers can change the selected main task's model and permissions. The context composition reads layers for model, effort, thinking, and permissions; the tool executor can return `newContext`; the main query incorporates it and supplies the resulting context to its next turn. Engine `[201213000,201218850)`, `[213041300,213043800)`, and `[213047450,213050250)` establish this main-task path. It would be wrong to dismiss all layers as isolated subagent settings.

However, this does not establish a requirement for an active registry of every fork, tool scope, request context, or concurrent inference. The accepted field is the model configuration applied to the selected ordinary task at its endpoint samples. The producer should identify the relevant main-task context and include the model settings actually read from it. Effort, thinking, advisor, or similar facets belong where they affect that task's model configuration; enumerating unrelated contexts would strengthen the claim.

The access report's suggestion to use existing getters therefore needs one qualification: a complete sample must reconcile their configured session model with any applicable main-task layer at that sample. A context-usage summary is not a substitute. In this headless path, `contextUsageInputs` lacks the running-turn model override found in a different UI path; summary resolution can also emit a once-only model warning. Engine `[221137000,221140650)` and `[200484400,200485700)` show why summary acquisition has different meaning and effects.

The remaining source question is the lifetime and availability of the selected main-task context at both endpoint samples, including when no turn is running. A small descriptor for that context may suffice. A universal active-context registry is a proposal whose necessity has not been established. Per-attempt and backend-model proof remain excluded.

### Full permissions require applicable decision inputs, not an unlimited inventory

Both reports correctly reject a mode label and the three rule lists as the entire applied permission configuration. The Engine permission context and layer composition include mode rewrites, tool narrowing, prompt avoidance, directory scopes, sandbox behavior, and runtime flags. Desktop can also contribute decisions such as browser or computer-use grants. A facet belongs in the complete sample when it can change permission for a tool or operation available to the selected task at that sample. It need not have been exercised to be applicable.

The state report's broad lists must be filtered by that relevance test. An unrelated task's consent, an unavailable tool family's state, or an isolated fork's override is not mandatory merely because a producer exists. Conversely, a selected task's enabled browser grant cannot be omitted merely because its before/after fixture did not invoke the browser. Conditional applicability must come from source and selected configuration, not assumptions about likely use.

Existing `list_rules` serializes a represented and filtered rule view, including inactive managed-only rules and directories. It does not itself expose every operative permission input. Engine `[231927050,231928958)` and `[201213000,201218850)` distinguish the view from the context that decisions consume. Raw inactive stores can explain a difference, but requiring every raw store regardless of effect would be stronger than the accepted applied-state comparison.

Pending changes also need this filter. Include selected-task changes that can alter a compared field: model, permission mode, rule or directory application, relevant MCP/tool availability, account binding, cwd, and worktree transitions. Include unresolved permission decisions where they affect its grants or active configuration. Generic hook or user-dialog requests are not automatically pending configuration changes. Engine `[220374464,220375480)` exposes such request categories without proving that all are relevant.

The Desktop broker's `hasPendingFor` skips out-of-turn requests, so that predicate alone is insufficient for a complete selected-task pending projection. A new projection must filter actual entries by selected binding and relevance. Iterating a global broker map acquires other entries' identifiers even if output retains only the selected task; permission for that scan or a selected-task index belongs in the later intervention proposal. Neither output filtering nor a read-only name eliminates acquisition.

### Applied account route remains missing, but the acknowledgement producer already exists

The Manager's selected-stream account intent, cached profile, SDK initialization account data, and status account text do not prove the account, organization, and authentication route actually in effect for the selected query. The state report correctly requests a nonsecret descriptor of the selected Engine binding and route, with provenance. Provider selection can depend on model, environment, base URL, generated authentication, and explicit header overrides. Engine `[198737300,198740000)`, `[203886700,203896950)`, and `[200140524,200142150)` establish this conditional route structure.

The applicable route family must be closed for the chosen candidate, rather than every retained provider implementation being mandatory in every sample. A configured but untraced route is an explicit qualification gap. A family demonstrably absent from the selected configuration is inapplicable. This preserves the actual-route requirement without requiring proof of every possible provider or server-attributed identity.

I correct the implication that Engine environment acceptance has no producer. Engine `[220379600,220381850)` accepts or refuses inbound environment updates, validates the values, applies allowlisted keys, invalidates authentication caches, and emits a success or error `control_response` when an optional nonempty `request_id` is supplied. Refused worker updates return without that success acknowledgement. The existing Desktop token push in Manager `[467500,471200)` sends `update_environment_variables` without a `request_id`, so its successful enqueue and `pushed` record still do not witness Engine acceptance.

The missing witness is in the selected Desktop integration path, not an absence of acknowledgement capability in the Engine. Whether adding a correlated acknowledgement to that path is necessary, sufficient, and compatible needs a concrete source proposal. Even an acknowledgement proves environment handling, not the final authentication route: subsequent providers, caches, and request overrides can affect that route.

An observer must not call the client constructor or token provider to discover the route. The constructor path includes refresh and helper/client work. A diagnostic producer must describe already established selected binding state, identify a not-yet-established route where appropriate, and avoid refreshing credentials or creating a request. Source-derived intentions and observed local binding must remain separate.

### Location has a direct Engine gap and a separate unresolved owner boundary

The raw Engine cwd comes from its AsyncLocalStorage scope or current cwd source; the public presentation getter catches failure and substitutes the original cwd. An adapter using that presentation cannot distinguish a genuine current cwd from fallback. Engine `[198480300,198481850)` supports a raw selected main-scope projection with failure provenance. This is about the ordinary task's cwd; every nested scope's cwd would be a stronger field.

Registered worktree is a Desktop owner question. The Manager's harness cwd generation and cached worktree projection can be copied without resolution, but the resolution path can save, adopt, and watch state. Manager `[508250,511500)` establishes these effects. The allowlist does not establish a callable, nonmutating authoritative registry read from the owner reached there.

The state report's proposed resolution-state descriptor is useful if the owner lacks suitable current state. It is not yet proven that the owner needs modification. The named follow-up is the exact retained source for `gitWorktreeManager.getWorktreeForSession`, its registry, and relevant invalidation/lifecycle paths. Do not invoke resolution merely to make a diagnostic field appear current.

## Mechanism decision and concrete costs

An app adapter alone does not satisfy the accepted fields. Existing renderer IPC is tied to an admitted sender; internal methods are not a standalone attach interface. The SDK getters require an already owned query. Creating or resuming a query, direct-connect provisioning, reinitialization, and a second stream consumer change the mechanism and can change the selected execution. None establishes passive external access.

The smallest useful design is a finite Manager adapter attached to an independently selected existing query, paired with a narrow Engine diagnostic request for otherwise inaccessible selected-task state. That Engine change should expose the relevant main-task model context, raw permission context and applicable layers, raw cwd/fallback classification, already applied account route/binding provenance, and specifically relevant pending application state. Existing producers should be reused where their meaning and availability match. New status records are needed only for concrete missing transitions; the proposal must prove their update and retirement paths.

This is a separate source-change proposal, not permission to patch the Engine. Its costs include a diagnostic protocol branch and SDK/Manager access wiring, any necessary selected-context or route-lifecycle records, serialization and validation, version binding, and restoration of all modified artifacts. Exact insertion count and footprint remain unresolved until that source proposal exists. The actual RC wrapper source is also needed to prove that the proposed owned-query access matches this Desktop build; the stable SDK is comparative evidence.

The app side still needs exact loader placement, finite admission/output code, selected-query binding checks, and cleanup. A selected-query fallback tap in the existing receive loop is an optional diagnostic adjunct for observed fallbacks during a declared interval. It must not add a second consumer, and its coverage must be demonstrated through the normalizer. It does not create an every-attempt requirement or recover events before admission.

Startup insertion requires loading the modified app. A restart replaces or interrupts the current query and cannot preserve its binding. No verified hot-load surface for the already running ordinary task is established here. A candidate loaded before a fixture can subsequently be bound to that fixture, but this must be stated in the later qualification design. Transfer to the ordinary source remains a separate proof; matching restored files does not prove unchanged running behavior.

## Actor, clock, and acquisition contract

Each value must name its producer and acquisition: synchronous Desktop state at adapter read time, asynchronous Engine response over the captured query, or an event observed in the owned receive loop. Preserve separate start/end times and binding checks for each acquisition. These samples are not atomic and do not establish an interval-wide invariant.

Time-dependent Desktop grants require the evaluated time and relevant policy/TTL inputs. The computer-use helpers can accept a supplied time and filter expiration; copying stored entries without that evaluation changes the field. Capturing one clock value is useful for a host-side projection but does not synchronize an asynchronous Engine sample.

SDK getter replies can acquire settings, rule, or status material beyond the retained output whitelist. Output caps do not bound that upstream acquisition. The later authorization must cover the exact request and reply scope, any broker scan, and proposed descriptors. Report overflow or unavailable provenance as incomplete; never silently truncate and declare full applied configuration.

The public SDK getter methods have no timeout argument. An adapter-side promise race stops waiting but leaves the request pending; internal request cancellation adds access wiring and can send a cancellation frame. The proposal must account for late replies, pending callbacks, output disposal, and expiration without closing the task's owned query. It must also distinguish its own diagnostic pending work from preexisting task configuration changes.

## Smallest useful next increment

Freeze a selected-task applicability and producer map before writing an adapter. Trace the ordinary main-context lifetime, applicable permission inputs, chosen authentication family and binding lifecycle, raw cwd scope, and relevant pending lanes. Request only the two additional artifacts already named: the actual RC SDK wrapper and the registered-worktree owner's source. These are source follow-ups, not live reads.

Then draft the minimal Engine diagnostic and Manager adapter changes together, with exact load path, selected binding, acquisition and retention, timeout behavior, interruption, restoration, and maintenance costs. That packet can support the mechanism choice after the joined findings receive independent review. This exchange supplies corrections and a narrower design horizon; it does not independently review or adopt the candidate.
