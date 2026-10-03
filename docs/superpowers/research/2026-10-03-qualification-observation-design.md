# Observe the selected task's qualification state

The existing query getters and a small Desktop adapter can supply useful qualification observations, including the applied model setting. The inspected interfaces still leave gaps in the selected query's effective account route, full applied permissions, and current cwd provenance. Closing those gaps may require changes in Code itself. A Desktop adapter alone does not implement those missing producers.

This source design joins [Design complete qualification-state observations](https://github.com/nisavid/provingkit/issues/412) and [Compare access mechanisms for the qualification observer](https://github.com/nisavid/provingkit/issues/413). [Choose the qualification observation mechanism](https://github.com/nisavid/provingkit/issues/414) owns the next increment. No observer, Engine change, installation, or live experiment is adopted here.

## Accepted endpoint claim

The [qualification decision](https://github.com/nisavid/provingkit/issues/411#issuecomment-5972858593) requires before/after observations of:

- the model configuration actually applied to the selected ordinary task, with observed fallbacks recorded separately;
- the account, organization, and authentication route actually in effect for its query;
- its applied permission configuration: active mode, effective rules and grants, applicable runtime inputs, and pending changes;
- its registered worktree and current cwd.

Saved preferences, cached profile metadata, and intended settings alone are insufficient. The claim concerns endpoint samples with individual observation intervals. It does not require server-attributed account proof, the backend model serving every inference attempt, an atomic snapshot, or continuous preservation throughout the interval. Full snapshots belong to qualification and affected requalification; ordinary notifications retain their separate peer, consent, delivery, and acknowledgment contract.

## Coverage follows the selected task

Each proposed field needs one of three dispositions: included with a named consumer that applies it to this task; excluded with source-backed applicability evidence; or unresolved with the exact missing relevance or producer fact.

An enabled browser grant can matter even if the fixture never opens a browser. An unrelated task's grant does not belong merely because the same manager stores it. Likewise, an applicable main-task model or permission layer matters, while every fork, served call, unused provider family, and bookkeeping request is not automatically a required observation.

Pending coverage includes task-bound changes or decisions that can affect the compared fields. Generic dialogs, unrelated queues, and observer-owned getter requests are not automatically pending permission configuration. Preserve genuinely relevant out-of-turn requests; Desktop's `hasPendingFor` omits them. An incomplete inventory must identify its missing applicable category rather than impose an unspecified universal inventory.

## Field-to-producer contract

| Field | Useful existing producer | Required distinction or remaining gap |
| --- | --- | --- |
| Applied task model | Captured query's `getSettings().applied`; selected/confirmed/pending app state | `applied.model` reads current Engine configuration, beyond a saved preference. Determine whether an applicable main-task layer changes that configuration independently. No all-context registry or per-attempt proof is required by default. |
| Observed fallbacks | Represented Engine fallback events and manager fallback state | Preserve actual normalized schema, observation interval, covered types, and overflow. A finite callback in the existing receive loop is proposed; it supplies no retrospective complete history. |
| Effective query account/org/auth route | Spawn-bound identity, cached initialization, status metadata, and host token-push state | These are supporting facts. A query-bound descriptor of the selected effective credential/route and applicable principal/org provenance remains missing. Do not refresh credentials or construct a client merely to observe it. |
| Engine applied permissions | Existing rule/directory response; event-time/host mode facets; traced permission composition | A fresh raw mode and applicable runtime/context inputs are not all exposed by the rule projection. Include relevant pending application state. Preserve exact represented rules, order, source, inactive status, and coverage. |
| Desktop effective grants | Browser/computer-use evaluators, broker/policy stores, and selected task state | Trace applicable consumers and evaluator inputs. Time-dependent grants require their evaluation time and expiry policy. Cold helper/cache effects and inaccessible selected-task pending categories remain gaps. |
| Registered worktree | Manager association, resolution generation, and cached resolved fields | The authoritative worktree owner and invalidation paths need inspection before choosing a new status record. Missing cached cwd does not distinguish pending, failed, absent, or cleared association. Do not invoke a mutating resolution to fill it. |
| Current ordinary-task cwd | Engine helper and status/Stop projection | The presentation helper can substitute original cwd on failure. The sample needs the selected task's raw read, scope, and explicit fallback/failure provenance, through a new producer or a demonstrated equivalent. |
| Selection/query/executor | Prospective fixture witness, current Code ID, held record/query/stream references | Independently bind the task and actual executable. A source pin, title, PID, request ID, or historical Code ID alone is insufficient. Recheck lifecycle around asynchronous acquisitions. |

Every observation records its producer/source identity, task/Code/query binding, acquisition interval, status, value, coverage, and gaps. Status distinguishes observed, missing, unsupported, failed, timeout, over-limit, and changed binding. An authoritative empty collection differs from an unavailable one. Compare only matching meanings and coverage, with applied and pending comparisons separate. Missing required evidence yields an incomplete result even if other values match.

## Corrections established by the exchange

The [state first report](2026-10-03-qualification-observation-sources/state.md) and [access first report](2026-10-03-qualification-observation-sources/access.md) were independently frozen before exchange. The [state cross-examination](2026-10-03-qualification-observation-sources/state-cross.md) and [access cross-examination](2026-10-03-qualification-observation-sources/access-cross.md) refine them. This synthesis controls their current interpretation; historical proposals in the first reports are not additional requirements.

**Model scope.** The applied getter reads current configuration. The exchange also traced `newContext` back into the main query's next-turn context, so relevant layers cannot all be dismissed as subagent-only state. Whether a particular layer changes this ordinary task's endpoint configuration remains a bounded applicability question. The corrected contract requires that check, without treating every context registry and thinking option as a mandatory new producer. Decisive Engine anchors are `[221116400,221117650)`, `[221225050,221226960)`, `[201213000,201218850)`, `[213041300,213043800)`, and `[213047450,213050250)`.

**Environment acknowledgment.** Code can emit a correlated success/error response for an environment update carrying a nonempty `request_id`. The inspected Desktop token-push path sends no such ID. Its enqueue/pushed record therefore supplies no acceptance witness; the missing witness is in that integration path, not a total absence of Engine support. Acknowledging environment handling still does not prove the final effective authentication route. Decisive anchors are Engine `[220379600,220381850)` and Manager `[467500,471200)`.

**Sandbox dialog.** The exchange found the existing `getSandboxDialog()` route. It combines configured restrictions with runtime-derived fields, invalidates settings, and may check or seed dependencies and update caches. It is useful diagnostic evidence with operating effects, not a passive complete applied-permission snapshot. Do not silently add it to the sample. Anchors are SDK `[1108100,1108350)`, Engine `[221196668,221197080)`, `[232011440,232012820)`, `[197935800,197938700)`, and `[202839900,202841200)`.

**Worktree owner.** The manager's resolution path has effects, but that does not establish that the underlying worktree owner lacks an adequate getter. Inspect `gitWorktreeManager.getWorktreeForSession`, its registry, and invalidation/lifecycle source before selecting an owner change. The currently inspected Manager anchor is `[508250,511700)`.

All anchors are zero-based, end-exclusive byte intervals into the retained artifacts identified in the raw reports. Their [manifest](2026-10-03-qualification-observation-sources/manifest.json) preserves exact report bytes and digests. Desktop 2.9939.4 and its declared Code/SDK RC targets are assessed source identities, not observed running executors. The public stable SDK is comparative evidence; the actual RC wrapper still needs verification. Changed builds receive graduated compatibility assessment, not automatic rejection as incompatible.

## Access alternatives and actual effects

| Access choice | What is established | Cost and limitation |
| --- | --- | --- |
| Existing renderer IPC | App-bound methods reach selected manager observations and some query getters | A verified authorized renderer caller and independently selected task are still needed. Cold calls may load modules; control requests add scheduling, accounting, validation, and logs. Available fields are partial. |
| Desktop-owned MCP | An owning-task tool can format selected manager records | A new prompt/tool call has conversation and usage effects. Lookup may load storage or check folders. Recorded values do not become applied Engine state. No external listening endpoint is established. |
| Existing SDK query | Correlated getters work on a query already owned by the caller | Obtaining the exact Desktop-held object is unresolved externally. Creating/resuming a query, direct-connect provisioning, reinitialize, and a second stream consumer do not establish unchanged passive attachment. |
| Finite Desktop diagnostic adapter | A concrete integration point beside the existing manager singleton can receive that manager and its captured query | Exact loader/module/protocol bytes are unimplemented. This exposes app-held state and existing getters, but cannot read missing Engine-local fields directly. Startup loading can require a candidate launch and interruption/rebinding. |
| New Engine diagnostic producer plus app access | A source proposal can name the missing account, permission, cwd, and applicable main-context fields | An editable canonical source, build/load method, exact change footprint, and restoration path are not established. This is a separate intervention from a Desktop module and remains a feasibility choice. |

The native inbox delivers receiver input; it is not a control-getter transport. A getter-shaped inbox message remains input. Reinitialization resends configuration and can replace hook callbacks or redeliver pending requests, so it is not selected as a fresh getter.

The proposed app adapter would receive the existing manager, accept a configured exact task/Code binding, and admit two finite `before`/`after` phase slots. Named request/result files are one possible interface, adding polling, filesystem I/O, and retention. No socket or ongoing service is selected. Before configuration admission, the adapter collects no task state. After completion or expiry, it releases its own timers/listeners without closing the task's query.

Capture the selected record, query, stream, Code ID, lifecycle, and available prompt epoch. Recheck them around each asynchronous operation. Desktop's request-accounting helper can return an old query's reply after replacement; the observer must retain it as old-query evidence and mark the intended sample incomplete. Reference/epoch checks need coverage of query installation and retirement paths before implementation.

A promise race bounds waiting, not execution, reply bytes, or retained request handlers. Internal cancellation adds a protocol operation and effects; it needs its own choice. Output filtering or caps do not bound whole settings/rules/status replies already acquired by the SDK. A global pending-map filter reads other entries' identifiers before discarding them. The actual proposal must cover those acquisitions or supply a different producer.

## Collection and interpretation

1. Bind the reviewed source/executor compatibility and the independent task witness. Preserve Desktop task, Code conversation, query, stream, endpoint, and executor identities separately.
2. Capture the selected existing query and app state through the chosen access path. Do not start, resume, warm, reinitialize, or replace a task to impersonate attachment.
3. Acquire only approved existing replies or implemented owner projections, with individual intervals, full acquisition footprints, support outcomes, and binding checks. Keep cached initialization and event-time values dated.
4. Sample required before/after endpoints without forcing pending work to settle. Record observer-induced requests separately from the task's pending changes.
5. Compare covered facets as same, changed, or unknown. Equal endpoint values do not prove continuous preservation. Retain partial results and unresolved required facets explicitly.
6. Dispose only introduced observation resources and verify the selected restoration/disposition separately. No automatic retries, additional inference, or wider discovery fills gaps.

Computer-use grant expiry requires the evaluator's clock argument. Monotonic timestamps from different processes cannot be directly compared. A single phase label does not make host and Engine samples simultaneous.

A startup-loaded candidate observes its own query after launch and selection. Restarting ordinary Desktop changes query objects; a resumed Code ID does not preserve the old query. The former archive patch, two restarts, and receipt deadline are not inherited. Candidate results need an explicit argument and observations supporting transfer to ordinary Desktop. Restored file hashes establish content, not restored running behavior.

## Next bounded choice

The reviewed evidence supports a source-feasibility decision before more adapter implementation:

- trace the selected ordinary-task context and applicable permission/account producers, with explicit included, excluded, and unresolved facets;
- inspect the actual RC wrapper and worktree owner's source;
- establish whether a narrow Engine producer has a practical source/build/load route, or whether an equivalent existing producer can close the named gaps;
- return a concrete combined proposal with source changes, acquisition/effects, interruption, restoration, maintenance, and transfer costs.

This does not adopt an Engine patch. If that source/control surface is unavailable or disproportionate, return the specific gap and alternatives to the operator. Retaining existing partial observations remains possible, but does not satisfy the unchanged full qualification claim.

A later single-getter check on an independently bound disposable fixture can test support, correlation, shape, and effects. It cannot qualify unimplemented fields. The [smaller fixture-binding design](2026-10-03-fixture-binding-design.md) and its mechanism choice continue independently.

Under `capturing-agent-procedures`, qualification preparation must load this synthesis, the accepted decision, exact supporting reports, and the eventual chosen producer/access design, recording the reviewed revisions consumed. Return corrections to those sources. This is a provisional research procedure; no installed skill, live controls, authentication/containment/private-data protections, or route qualification is certified. No implementation, tests, private receiver reads, or live actions were performed in this increment.
