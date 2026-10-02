# Minimal app-side observation candidate

**DONE_WITH_CONCERNS.** The smallest app-side competitor worth retaining is a selected-query observation bridge: bind one Desktop task to its existing Code query, export bounded state observations, and keep delivery and acknowledgment evidence with their actual producers. The retained observer already demonstrates those mechanics synthetically. It does not supply fresh, complete applied state or qualify a notification route.

I recommend retaining the current prototype as comparison evidence, with an eight-anchor access-and-binding core and two conditional permission-mode witnesses. I would add no receipt instrumentation or rebuild an archive in this increment. The final hook and field selection belongs after the frozen exchange.

This report preserves the accepted same-machine, exact-peer contract, receiver-origin delivery, explicit correlated acknowledgment, unknown-send reconciliation, distinct held/refused states, and before/after actual account, model, applied permissions, and worktree/cwd observations. Busy continuity remains diagnostic. The common [reviewed comparison](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/research/2026-10-01-observer-scope-review.md) and [method](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/research/2026-10-01-observer-scope-review/method.md) are prior evidence, explicitly shared before this independent lane.

## Architecture and callable access paths

The app-side bridge selects a configured Desktop task from the manager, requires a local available record, and captures its Code session ID, query, input stream, generation, and getter references. It rechecks those identities around collection and publication. Missing or replaced queries stop observation; the source supplies no fallback task, prompt, resume, or temporary query. See `createDesktopAdapter` and `captureCandidate` in [the adapter](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/prototypes/desktop-observer-probe/desktop-adapter.mjs#L447) and [probe](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/prototypes/desktop-observer-probe/observer-probe.mjs#L733).

The actual external access path is narrower than those internal symbols suggest:

| Surface | Reachability established by retained source |
|---|---|
| `PROVINGKIT_OBSERVER_CONFIG` | Launch-time configuration path consumed by the inserted sidecar. |
| `bootstrap.json` | App-produced binding record readable from the configured private run directory. |
| `arm.json` | Externally constructed, exact-binding input accepted once before collection. |
| `sample-NNNNNN.json` | Bounded app-produced observations, acquired by the standalone reader. |
| `record.query.accountInfo`, `getContextUsage`, `listPermissionRules` | Internal calls on the captured existing query; no external query attachment is established. |
| Desktop host `get_session` | Hosted inside Desktop-owned Code queries; no external read endpoint is established. |
| Renderer `LocalSessions.getSession` | Electron renderer binding; no standalone transport address is established. |

The bridge adds neither a socket nor generic Electron/query RPC. Its current lifecycle is one shot per manager: `bootDesktopObserver` marks the manager before startup, awaits one arm, collects bounded samples, and disposes the adapter scope. It has no implemented continuous service or repeated per-notification rearming interface. See [bootstrap lifecycle](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/prototypes/desktop-observer-probe/desktop-adapter.mjs#L725) and [file protocol](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/prototypes/desktop-observer-probe/observer-probe.mjs#L1108). The common [source delta](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/research/2026-10-01-observer-scope-review/native-source-delta.md) bounds the host/renderer findings to four inspected members.

## Requirement-to-producer comparison

All app-side reads below require a separately authorized modified-app launch and selected fixture-data scope. Existing-file reads require their own selected-file scope. No such access was exercised here.

| Requirement | Producer/interface and exact-task binding | Freshness and applied-versus-saved meaning | Gap and smallest discriminating check |
|---|---|---|---|
| Exact task/query | Manager selection plus task/Code IDs, record view, query, input stream, generation, and getter-reference checks | Rechecks current object relationships during collection | Native peer-address mapping remains separate. Later compare the fixture’s own peer identity with fresh native discovery. |
| Account route | `spawnAccountOf(record)` and query `accountInfo()` | Spawn identity is historical; `accountInfo()` is initialization cache | No fresh authenticated-route producer. Trace or obtain a receiver-bound post-refresh route observation. |
| Model | Existing query `getContextUsage({detail:"summary"})` | Query response carries a model; next-effective-model meaning is unproved | Later compare it with an authorized fixture model transition and an independent executor report. |
| Permission mode | Manager `permissionMode`, retained Code init/status mode event, in-flight mode-request count | Separates manager selection, last Code report, and pending setter activity | No fresh arbitrary mode getter; event silence is insufficient. Verify initial/event coverage and a pending/completed transition. |
| Rules and workspace grants | Existing query `listPermissionRules()` | Projects rules, sources, behavior, editability, inactive markers, workspace directories, managed-only flag, and error count | Executor support and coverage remain unqualified. Verify known applicable rules and settings-error behavior. |
| Host grants | Manager `alwaysAllowedReasons`, computer-use app/flag stores, and effective app/flag functions | Current selected host projections, separately from Code rules | Complete applicable grant inventory is unproved. Trace every relevant grant consumer and mutation path. |
| Pending changes | Update types, flag-sync marker, mode requests in flight | Selected markers; source explicitly returns `pendingCoverage:"unknown"` | False markers do not prove no pending/failed change. Compare with authorized queued and failed fixture updates. |
| Worktree/cwd | Manager `harnessCwd`; selected metadata worktree/path projection | `harnessCwd` is last manager-observed state; cwd event provenance is unavailable. Rules response `originalCwd` is historical | Need current executor cwd and worktree association. Compare manager state with a bound executor observation. |
| Delivery and correlated ACK | Separate selected transcript/session reader or qualified receiver event | A positive attributable receiver record may support delivery; explicit assistant ACK must name the correlation | The app state bridge has no external-native delivery producer. Confirm the chosen sender’s actual receiver record and ACK grammar on disposable peers. |
| Unknown, held, refused | Chosen transport’s admission/outcome producer plus receiver reconciliation | Held may later release; refused drops; absent evidence remains unknown | No state snapshot or quiet file resolves these outcomes. Qualify the route-specific evidence and reconcile without resend. |

The producer distinctions follow [field producers](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/specs/2026-09-29-desktop-runtime-observer-design.md#L157), [host projection](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/prototypes/desktop-observer-probe/observer-probe.mjs#L425), and [getter projections](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/prototypes/desktop-observer-probe/observer-probe.mjs#L661). This is factual permission-configuration coverage, without a general security or enforcement assurance claim.

## Which hooks earn retention

The current [patch manifest](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/prototypes/desktop-observer-probe/manager-patch.json#L8) contains ten replacements:

- **Loader and singleton attachment: two anchors.** They provide access to the actual manager and its existing query. An ordinary standalone SDK query would observe another executor.
- **Query installation and teardown: two anchors.** They advance generation when the observed executor lifecycle changes, preventing a multi-getter collection from crossing a replacement boundary unnoticed.
- **Rewind, resume, clear, and init Code-ID assignments: four anchors.** They invalidate a collection when lineage changes, including changes away and back that endpoint ID equality alone could miss.
- **Init and status mode reports: two anchors.** They preserve Code-event provenance for comparison with manager selection and pending requests. They do not establish fresh mode at every observation point.

The first eight form the minimum source-backed access-and-binding hypothesis. The last two remain justified only while a qualified narrower surface cannot supply the needed bound mode reports. An eight-anchor candidate has **not** been implemented or reviewed; deleting those hooks would change the current candidate and its evidence.

Additional account, cwd, permission, or native-inbound hooks need named producers and coverage first. Adding callbacks around unavailable state would create more instrumentation without closing the requirement.

## Task binding and bounded fixture discovery

Identifiers have distinct jobs. The Desktop task ID names the metadata file. Its contents provide the Code ID for query/transcript binding. Native peer references and `bridgeSessionId` are separate identities. I independently rechecked `getSessionFilePath` and `writeSessionToDisk` in the pinned manager: the filename is the Desktop ID plus `.json`; no Code ID is required to name it. The manager recheck covers UTF-8 byte spans 919450–919900 and 937550–938330, consistent with the [acquisition-path report](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/research/2026-09-29-desktop-observation-paths.md#L54).

A smaller discovery proposal would permit:

1. One explicitly bound user-data root and declared metadata subtree.
2. Identifier-only directory-entry observations within a stated depth/count bound; no sibling record contents.
3. An independent exact Desktop ID obtained from the normal fixture-creation UI or a proven existing event.
4. One derived metadata read retaining only the approved identity/path/lineage projection.
5. Matching Desktop ID, Code ID, project identity, and allowed lineage before observer configuration.

If account/organization directory names are unknown, their enumeration must be explicit additional scope. Filename novelty or newest modification time may find candidates; neither proves which candidate belongs to normal fixture creation. Without the independent selected-ID witness, this proposal remains incomplete.

The receipt alternative supplies stronger same-process registration, writer, account-transition, metadata, and query-handoff relationships at greater cost. Its provisional writer witness is distinct from accepted admission. Admission requires matched selected metadata, final configuration validation, guard closure, and the frozen query/input-stream/generation handoff. The `initiator:"user"` discriminator does not authenticate a click. See [receipt claim](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/research/2026-09-30-fixture-identity-acquisition-design.md#L11) and [continuation](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/research/2026-09-30-fixture-identity-acquisition-design.md#L212).

If that receipt procedure is retained, preserve its accepted 15-minute acquisition-admission ceiling: readiness to admission authorization, with expiry rejecting acquisition without retry. Publication and restoration may take longer. I would not transfer that clock automatically to a different discovery procedure.

## Diagnostic use, ongoing use, and recovery

For temporary diagnosis, the retained operation exchanges the installed archive while Desktop is stopped, launches the candidate, collects bounded observations, stops it, restores the pristine archive, and launches the original. That entails two restarts and potentially interrupts existing work. The total window remains unmeasured. Package identity must be rechecked before restoration; an intervening update prevents blindly restoring an older archive. Restored bytes and restored task behavior require separate verification. These are documented proposed operations, without live execution evidence. See [operating effects](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/prototypes/desktop-observer-probe/packaging-evidence.md#L95).

A diagnostic result transfers to unmodified Desktop only as far as its evidence supports. Getter support, projected response shape, and observed instrumentation behavior describe the candidate. Transfer of notification findings additionally needs source analysis of observer effects, relevant matched candidate/restored behavior, and receiver-origin evidence on the unmodified route. An unmodified operating route still needs its accepted endpoint observations; a successful instrumented sample cannot supply later unavailable measurements.

As an ongoing dependency, the bridge would require a maintained package integration, launch configuration, private output/retention policy, update assessment, stale-output rejection, and recovery when the observer or query disappears. The present one-shot, three-sample prototype cannot serve that lifecycle. A reusable observer needs an explicit repeated-collection/rearming design and an owner; permanent archive modification alone does not provide it.

Compatibility should remain graduated per lifecycle binding, getter, projection, grant inventory, file protocol, and receiver representation. New builds begin unassessed. Compare consumed behavior first, reuse justified unchanged evidence, and repeat affected live checks when cheaper evidence leaves uncertainty. Changed build inputs require a rebuilt and verified candidate before later installation.

## Prototype disposition and smallest later checks

**Reuse the retained prototypes; build nothing new in this round.** The [synthetic observer](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/prototypes/desktop-runtime-observer/README.md#L69) already demonstrates binding, deadline, late-result, partial-field, export, and reader behavior. The probe adds the concrete adapter and bounded file handshake. Its limits are three samples, a 30-second observation window, at least five seconds between samples, and at most two seconds per getter. These are collection bounds, not guarantees of request cancellation or underlying value freshness. See [contract constants](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/prototypes/desktop-observer-probe/observer-contract.mjs#L33).

The prototype’s public test boundary is `attachProbe({selectReceiver,…})` plus exported-envelope inspection. Synthetic inputs can resolve whether collection rejects replacement, deadlines, malformed projections, and stale bindings. They cannot establish a real producer’s freshness, complete permissions, external-send record shape, or query-to-OS association. A toy receipt parser would merely encode the unresolved assumptions.

This round independently recomputed all eight build-input digests; all match the retained receipt. The pristine manager is 1,596,495 bytes with SHA-256 `bd2144a3653bb843f4b75fe652124a4e478f273b5f6c2e10a2139fa3a9a3152f`; all ten patch anchors occur exactly once. The retained [build receipt](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/prototypes/desktop-observer-probe/candidate-build.json) says `runtimeExecuted:false`. I did not rerun historical tests, rebuild, or inspect the staged archive.

The smallest later live sequence, if separately selected and authorized, is:

1. Verify normal disposable-fixture creation, exact identity, candidate loading, and one existing query binding.
2. Perform a no-send sample of only the selected residual producers; report support, timings, gaps, and receiver effects.
3. Use controlled fixture transitions only where required to discriminate freshness or applied-state meaning.
4. Qualify the native sender’s actual receiver record and explicit correlated ACK, preserving held/refused/unknown distinctions.
5. Exercise idle and busy receivers with complete before/after observations; retain busy continuity as diagnostic.
6. If claiming transfer, obtain the relevant unmodified-runtime evidence after verified restoration.

No current combination closes fresh account, complete applied permissions, current cwd, native address binding, or external delivery/ACK.

## Procedure handoff and exposure record

I used `research` and `capturing-agent-procedures`. This lane consumes the reviewed comparison method; it proposes a residual observer and bounded discovery alternative without installing either as a convention. The join should retain this report’s source revision, identify which observations survive comparison, and connect any selected procedure to its maintained source and consumer invocation. The existing [procedure capture](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/prototypes/desktop-observer-probe/procedure-capture.md#L1) governs the experimental probe. Cross-examination and current final reviews remain coordinator-owned later work.

**Input log:** I read only `coordinator-retained app r1 brief`; the installed `research` and `capturing-agent-procedures` skills; permitted repository inputs through immutable `git show` at `6fbddb3883e08476af9fffe1410863f0e89f0cd6`; and `offline source extraction/manager-pristine.js` for digest, anchor counts, and four bounded method spans.

Repository exposure comprised `CONTEXT.md`; the common synthesis and method; all six common conceptual/survey/native first and follow-up reports, `native-source-delta.md`, and `history-trace.md`; the runtime-observer design; fixture-acquisition design; observation-path report through line 155; runtime-observer README; and the probe README, packaging evidence, procedure capture, patch manifest, adapter, contract, selected probe ranges, build receipt, and its eight hashed input blobs. Oversized reads were followed by targeted reads where relevant output was omitted; no whole-file inspection is claimed for `observer-probe.mjs`.

No new sibling findings, memory, other chats, tickets, profiles, conversations, credentials, settings, live process data, or unrelated scratch were inspected. No external provider received app source. No public documentation was freshly fetched; inherited vendor claims remain dated prior evidence. I performed no writes, delegation, peer messages, tests, app execution, UI operation, installation, fixture creation, prompt, send, or restart.
