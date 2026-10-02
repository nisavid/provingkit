# Existing-interface observations: cross-informed report

**DONE_WITH_CONCERNS.** Bound stored-session reads plus narrowly selected receiver hooks are a credible lower-cost composite for identity, acknowledgment, and some event-time state. No current candidate closes fresh account-route observation, complete applied permissions, or arbitrary current cwd/model/mode sampling. The app-side bridge supplies access to the existing query, but its current producers remain incomplete.

I retain my first report unchanged as history. This report corrects its SDK acquisition assumption and incorporates the frozen hook and app-side findings.

## Revised component combination

Retain these components for comparison:

- Native MCP discovery and submission, with fresh exact-peer and purpose-consent checks before every send.
- One explicitly bound Desktop metadata acquisition for Desktop-to-Code identity and lineage.
- An authorized transcript acquisition or assessed SDK reader for positive incoming-message evidence.
- A minimal receiver command-hook projection, if selected, for Code session identity, socket address, final assistant ACK text, and useful event-time state.
- An app-side bridge only for named residual observations that need existing-query or host-state access.

This is a composite candidate, not an adoption decision. Hook activation changes receiver configuration; app instrumentation changes the tested application. Neither grants access to private fixture data.

The externally reachable SDK helpers and selected filesystem reads remain distinct from internal Desktop symbols. Host `get_session` is supplied to Desktop-owned queries through SDK MCP server objects. `LocalSessions` handlers are registered on particular `webContents.ipc` instances, with sender-frame validation. The inspected paths expose no independent attach address. Sources: pinned `.vite/build/index.chunk-CKt-cwRV.js`, `Gd` and `createProxyServers`; `.vite/build/index.chunk-DuaKZOPP.js`, `Oo`, `Ab`, and `Ob.for(webContents).setImplementation`. The [observer design](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/specs/2026-09-29-desktop-runtime-observer-design.md#existing-access-paths) records these chains.

A hook collector’s output log would be a new external observation interface. The app bridge likewise adds launch configuration and bootstrap/arm/sample files. Neither should be described as an existing externally callable Desktop getter.

## Cross-examination and dispositions

**The hook socket contribution is stronger than a generic identity lead.** Current documentation says `CLAUDE_CODE_MESSAGING_SOCKET` identifies the receiver inbox and is exported before hooks, including `SessionStart`, when messaging starts enabled. A receiver event containing Code `session_id`, paired with that environment field, offers a concrete Code-to-address join. It still needs qualification on the selected executor, comparison with fresh discovery, and linkage to the consented Desktop task. It supplies no consent or incoming-delivery proof. Exclude the messaging token and unrelated environment values. [Official socket contract](https://code.claude.com/docs/en/cross-session-messaging#the-sessions-inbox-socket).

**Prefer investigating `Stop.last_assistant_message` before `MessageDisplay`.** It can capture a final correlated ACK without waiting for transcript persistence. The official hook reference specifically warns that the final message may not yet be in the transcript at Stop time on every version. The pinned SDK declaration makes the field optional, so absence remains unknown. This strengthens the ACK candidate; it does not replace the independent incoming record or establish the adopted ACK grammar. [Stop input](https://code.claude.com/docs/en/hooks#stop), SDK 0.3.284 `StopHookInput`, declaration line 9437.

**Remove lease preservation from the hook coverage boundary.** The accepted observation concerns actual worktree/current cwd, account, model, applied mode/rules/grants, and pending changes. Worktree lease behavior is not an additional acceptance obligation supplied by this task.

**Treat the app-side eight-anchor core as a candidate-specific minimum hypothesis.** Its loader, manager attachment, lifecycle generation, and Code-ID invalidation hooks support coherent collection on that design. The count does not establish a globally minimal architecture, and it does not establish fresh account, model, mode, cwd, or complete permissions. Generation checks during a multi-getter collection address sample identity; they should not become a requirement to prove no transient change throughout the notification interval.

**My UI identity proposal remains hypothetical.** No inspected source or live observation establishes an ordinary externally readable task ID/permalink control. An internal creation return, host-produced link, or accessibility capability in Electron does not establish that surface. This harness’s native computer APIs are disabled. UI corroboration therefore contributes no currently demonstrated acquisition path.

## New SDK source findings

I inspected the public SDK 0.3.284 archive as data, without executing it. Two findings change my first report.

First, the SDK runtime can preserve useful origin evidence. `getSessionMessages` reaches `GD`, then normalization through `KD`; `gb` retains `origin` and timestamp. `Py` preserves non-task-notification origins, and `cb` recognizes peer-origin metadata for filtering. Current official documentation describes peer fields including decoded body and socket-derived PID provenance. This makes SDK delivery interpretation more concrete, while the actual external sender’s receiver row remains unobserved. The `SessionMessage` declaration does not enumerate all those runtime fields, so consuming them needs a pinned source dependency and compatibility assessment. [Public SDK archive](https://registry.npmjs.org/@anthropic-ai/claude-agent-sdk/-/claude-agent-sdk-0.3.284.tgz), `sdk.mjs`: `GD` byte 530964, `gb` near 529900, `Py` byte 392980; [peer-origin documentation](https://code.claude.com/docs/en/agent-sdk/typescript#peer-origin-fields).

Second, **an explicit `dir` is not an exact-file acquisition boundary**. `Vo` calls project-directory resolution and worktree lookup. `kn` enumerates directories; its long-path fallback can inspect other transcripts through `Aa`. `Vo` returns the first suitable result rather than proving candidate uniqueness. Supplying `dir` avoids the all-project fallback, but does not justify my first report’s narrower privacy implication. Source: the same archive, `Vo` byte 406889, `kn` byte 405187, `Vfe` byte 406645, and `Aa` near 404100.

Separate acquisition from interpretation. Use a separately authorized, bounded source of exact transcript bytes, or explicitly assess and authorize the SDK’s actual lookup scope. A projection’s retained fields do not describe every byte the acquisition reads.

## Compact coverage assessment

| Requirement | Best concrete candidate | Remaining producer or qualification gap |
|---|---|---|
| Desktop/Code binding | Selected metadata IDs and lineage | Exact file discovery and current receiver relationship |
| Native address | Hook Code ID plus exported socket, matched to fresh discovery | Selected-engine behavior and Desktop-task join |
| Receiver-origin delivery | Qualified SDK/transcript peer-origin record | Actual external native ingress, persistence timing, exact attribution |
| Explicit correlated ACK | Optional Stop final text; transcript fallback | Actual hook support, grammar, selected receiver, quotation/echo rejection |
| Unknown reconciliation | Positive bound delivery/ACK evidence | Absence remains unknown; no resend |
| Held/refused | Explicit native route admission/outcome records | No inspected collector exposes the complete selected-route state |
| Account route | Fresh executor-bound authenticated-route producer | No candidate supplies it; spawn/cache/storage facts are insufficient |
| Model | SessionStart/model-switch events; app query response | Event-time versus endpoint freshness and next-effective-model meaning |
| Applied mode | Hook event mode; app Code reports and pending setter state | Optional event coverage; no established arbitrary getter |
| Rules/grants/pending | Query rules plus applicable host stores and mutation outcomes | Complete combined inventory and applied/pending semantics |
| Worktree/current cwd | Hook cwd, selected paths, manager worktree reports | Endpoint currentness and coverage of Desktop worktree moves |
| Busy continuity | Existing idle/busy qualification diagnostics | Actual receiver continuation; no new pass threshold |

The applied-state gaps remain those in the [field-producer inventory](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/specs/2026-09-29-desktop-runtime-observer-design.md#field-producers-and-remaining-gaps). Combining partial observations does not make an uncovered field complete.

## Corrected identity discovery

I reverified `LocalSessions.start`: its successful comma-expression return yields `{sessionId}` with or without `typedText`; the conditional binding is a side effect. Exceptions can still reject it. The coordinator independently corroborated the same bytes. No external IPC access follows.

Keep two proposed discovery scopes separate:

1. **Directory entries only:** enumerate a bounded approved metadata subtree and retain names/file identities. This discloses sibling task identifiers, but cannot establish which new file belongs to normal fixture creation.
2. **Candidate content acquisition:** open separately authorized candidates and retain approved identity/path/lineage fields. The acquisition reads serialized bytes containing other private fields, even when the retained projection is small.

Matching needs an independent selected-task witness, matching filename/serialized Desktop ID, Code UUID and lineage, dedicated project identity, and creation provenance. Novelty or newest mtime is insufficient. If the independent ID comes only from an inaccessible internal return, this proposal remains incomplete.

The [receipt design](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/research/2026-09-30-fixture-identity-acquisition-design.md#claim-and-boundary) adds registration, writer fulfillment, transition bookkeeping, and same-query handoff. Bounded discovery is not an equivalent replacement. Those extra internal guarantees should be required only where the selected acquisition/collection claim needs them.

## Qualification and ordinary operation

Initial idle/busy qualification requires the accepted full before/after actual-state observations. Neither interval-wide invariants nor repeated full-state sampling for every ordinary notification should be silently added.

The contract clearly retains fresh exact-peer and consent checks for every send. It does not settle whether ordinary operation repeats all qualification measurements, uses a qualified compatibility policy, or samples state under defined conditions. The join should record that operating-policy ambiguity explicitly.

Temporary instrumentation can establish candidate getter support, source projections, timing, and observer effects. Transfer to unmodified Desktop requires a justified source comparison and relevant unmodified-runtime evidence. An instrumented sample cannot supply an unavailable ordinary measurement when the operating contract requires it. Conversely, if full sampling belongs only to initial qualification, an ongoing app observer is not automatically required.

Hooks avoid the planned archive exchange but add configuration, command execution, logging, activation/coverage checks, and callback effects. Late activation supplies no startup replay. The app candidate requires two planned restarts and maintained package integration; its current one-shot protocol may suit a bounded experiment, without establishing a recurring service. Both routes have unmeasured runtime costs.

## Prototype disposition and smallest checks

I revise the blanket “missing producers make new prototypes useless” conclusion. Source work already resolved two meaningful uncertainties: SDK origin preservation and acquisition breadth. A future targeted implementation could also test a public boundary that separates authorized acquisition from evidence interpretation, preserving optional origin fields, observation intervals, identity changes, and coverage gaps. Hook projection could test optional fields and collector discontinuity using the documented schemas.

Those tests would establish reader/collector behavior, not native ingress, Desktop hook activation, freshness, or permission completeness. Retained reader and observer demonstrations remain useful and were not rerun. No new implementation or test was authorized in this exchange.

The smallest later checks are:

1. Establish an ordinary exact-task identity surface, or select an explicit discovery scope; verify the actual acquisition footprint.
2. On an authorized disposable receiver, observe minimal lifecycle/Stop payloads, Code ID/socket relation, actual executor identity, callback coexistence, and latency.
3. Before claiming preservation, name and assess every residual applied-state producer.
4. After separate send authority, observe one actual native incoming record and distinct correlated ACK, including hook-versus-transcript timing.
5. Perform the accepted idle/busy endpoint proof, unknown reconciliation, and outcome distinctions. If instrumentation is temporary, obtain the evidence needed for transfer after restoration.

## Exposure and source identities

I read the versioned second-round brief, exchange manifest, all three frozen first reports, and coordinator source check. Their four SHA-256 values matched the manifest. My initial report remains unchanged. Repository evidence remains pinned to `6fbddb3883e08476af9fffe1410863f0e89f0cd6`.

Additional exposure comprised generic Context7 requests for official hook/socket contracts and the public npm archive read in memory. Archive SHA-256: `4550e830246026133fc1802a2208dd0f3a785cae1eec83f261d114c33d797771`; `sdk.mjs`: `32d062c37b03e10870fbf839f54694545ee01bc0ec719e47078fbed76e30ef71`. Public documentation was retrieved on 2026-10-02 and remains date-bound.

Private input locations were the second-round brief and exchange under `coordinator-retained dispatch records/`, the explicitly exchanged report paths, and the previously permitted offline source directory. I rechecked the `COPWZCsC` return and manager metadata-path method against their unchanged member digests.

I performed no writes, tests, app execution, private receiver reads, live operations, delegation, or tracker mutations. Under `capturing-agent-procedures`, this report is comparison input for the coordinator’s capture and final review; it installs no method and supplies no general security assurance.
