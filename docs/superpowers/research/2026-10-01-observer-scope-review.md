# Reassessing the Desktop observer

The first notification route has a credible native sender candidate. Modifying
Claude Desktop has not been established as necessary or sufficient to qualify
it. I recommend holding observer implementation while comparing existing
observation surfaces against the exact evidence still missing.

The earlier work investigated several native paths and reviewed the proposed
observer in depth. It did not first perform the independent conceptual search,
third-party survey, frozen exchange, and cross-examination used in the later
continuation investigations. This review supplies that comparison. It does not
claim an exhaustive search or qualify a live route.

## What has actually been done

The retained source at `c1d77f8dd6a5dab58f6dfd96275dff0ea6015ae0` targets
Desktop `2.9939.4` from the inspected `claude-desktop-extra 2.9939.4-1`
package. It includes:

- An internal metadata/transcript reader experiment and synthetic fixtures.
- An observer module, its adapter and reader, synthetic checks, a concrete
  archive patch, an offline archive builder and verifier, and launch/restoration
  procedures.
- An offline candidate archive whose retained build receipt explicitly records
  `runtimeExecuted: false`.
- A later design for acquiring the newly created fixture's identity. That
  mechanism is not in the built candidate.

The [patch manifest](../prototypes/desktop-observer-probe/manager-patch.json)
changes ten locations in one packaged manager JavaScript member and adds one
bundled helper. The hooks load the helper, track query installation and teardown,
track Code-session identity changes, observe permission-mode events, and attach
the observer to the existing session manager. The helper reads selected fields
from one configured existing query and exports bounded observations.

The proposed operation is to stop Desktop, exchange its installed application
archive for the candidate, start it with the current signed-in profile, perform
the disposable probe, stop it, restore the original archive, and restart.
That is a temporary package modification with two restarts. It is not a hot
patch of an already running process. Active work may be interrupted; the total
window is unmeasured. See the [packaging evidence](../prototypes/desktop-observer-probe/packaging-evidence.md)
and [operation proposal](../prototypes/desktop-observer-probe/application-operation.md).

No modified Desktop archive has been installed or launched in this task. No
live receiver probe, private receiver-content read, fixture creation, or
notification was performed. Separately authorized preparation reads collected
launch configuration; they did not observe an actual receiver's effective state.
Offline builds and synthetic tests do not establish app loading or live behavior.

The [receipt-adoption decision](https://github.com/nisavid/provingkit/issues/353#issuecomment-5925012453)
records the source direction and accepted 15-minute acquisition-admission limit.
That clock begins candidate readiness and ends acquisition admission. Expiry
rejects acquisition without retry; restoration may take longer. Implementation
is held for this broader scope review.

## Why the work moved toward instrumentation

The [sender investigation](https://github.com/nisavid/provingkit/blob/ee76e2a85c6cff97bd2111eefdc41fa6dfd433be/docs/superpowers/research/2026-09-26-claude-inbox-feasibility.md)
found `ListAgents` and `SendMessage` through the direct `claude mcp serve`
interface. It performed read-only discovery, not a send. Receiver evidence was
then investigated independently of transport.

The [observation-path investigation](2026-09-29-desktop-observation-paths.md)
identified metadata and transcript readers but showed why saved account,
model, permission, and worktree selections do not establish every effective
runtime value. The [observer design](../specs/2026-09-29-desktop-runtime-observer-design.md)
compared selected files, Desktop host `get_session`, renderer LocalSessions
calls, and controls on the existing query. It chose an app-side exporter as a
concrete route to some otherwise inaccessible state.

That led to a synthetic observer, an exact offline package candidate, a staged
probe procedure, and finally a fixture-identity receipt to resolve a setup
circularity: the observer configuration needed identifiers that had not yet
been acquired by the selected-file-only procedure. Each increment addressed a
real local problem. The sequence did not establish that the combined machinery
was the smallest architecture for the original task.

The security and implementation reviews answered questions about the chosen
mechanism's controls and behavior. They did not establish that simpler
architectures had been eliminated. Nor does the current observer solve every
remaining producer gap: account information may be cached or historical, model
freshness is not fully established, mode and cwd lack fresh getters, and the
combined applied permission state is incomplete.

## Separate the obligations

| Obligation | Existing candidate | What remains unproved |
| --- | --- | --- |
| Exact existing-peer selection | Native `ListAgents`, Desktop and Code identities | Fresh typed binding between the consented Desktop task and native peer address |
| Notification submission | Direct MCP `SendMessage` | Route-specific live admission and delivery behavior |
| Delivery and explicit correlated acknowledgment | Bound transcript/session reader, possibly native or host events | The selected external sender's actual receiver record, correlation grammar, and freshness |
| Before/after effective state | Existing query controls, host/renderer views, hooks, selected files, process evidence | Complete applied account/model/permissions/worktree observations for the same receiver |
| Disposable fixture acquisition | Normal task creation plus a selected identity read, or proposed receipt | A reviewed acquisition route with the required access and exact binding |

A sender does not need to own every observation. A file reader can establish a
positive record without establishing effective state; file silence cannot prove
non-delivery. Source evidence that a send does not reconfigure the receiver can
support preservation reasoning, but it does not substitute for the accepted
before/after actual-state observations.

The accepted claim concerns those endpoint observations. This review adds no
requirement to prove that every field remained constant throughout the entire
interval, to defeat a malicious same-user sender, or to make the receiver open
the context link. Held messages can later be released; held is not necessarily
terminal, and neither held nor refused causes automatic resend. Build changes
receive graduated compatibility checks, with justified reuse of earlier evidence.

## Independent comparison

The fresh conceptual lane started without project history or external solutions.
The external lane independently surveyed public interfaces, then expanded its
vendor-heavy first pass into five pinned third-party implementations. The native
lane audited the retained work. All first reports were frozen before exchange;
each lane then criticized the others and revised its own conclusions. Their
[follow-ups and source logs](2026-10-01-observer-scope-review/method.md) retain
corrections and coverage limits.

| Route or component | Practical benefit | Limit affecting the choice |
| --- | --- | --- |
| Native MCP sender plus selected transcript/SDK reader | Avoids Desktop package modification and an extra model-driven sender; may provide positive receipt and ACK evidence | External-send record shape, exact peer binding, and live freshness remain unproved; saved fields do not cover full applied state |
| Existing Desktop host or renderer reads | Reach some current manager values using existing code | An external selected-task accessor is not established; their field projections are incomplete |
| Receiver hooks | Documented lifecycle, mode, model, cwd, and assistant-display events could supply selected evidence without editing the app archive | Installing hooks changes receiver configuration; exact Desktop support, initial state, event coverage, incoming-message witness, and complete permissions remain unproved |
| Evidence-only UI/accessibility reads | May expose task identity, visible ACKs, and displayed settings without a package exchange | Displayed controls do not establish every applied value; reads still require selected-task binding and an approved observation scope |
| Remote Control reader/bridge | May reach an opted-in existing Desktop session | The inspected third-party bridge uses private endpoints and credentials, has mapping/pagination gaps, and sends user-role messages; it is not a supported peer-notification substitute |
| Current app-side observer | Has concrete source insertion, projection, offline packaging, and restoration work | Two restarts, package/update maintenance, private records, observation effects, and still-incomplete effective-state producers |
| CLI/SDK replacement session, terminal manager, or channel bus | Useful designs for other session owners and surfaces | No established attachment preserving this exact existing Desktop-hosted task and its full evidence contract |

The third-party survey inspected [cc-tap](https://github.com/es617/cc-tap/tree/b18e9a2f448bc83b338f444262e4f19d96f6c0c8),
[tmux-ccm](https://github.com/yohasebe/tmux-ccm/tree/32799c9d1ec9362101417c5beceaeb81aff88994),
[Recensa](https://github.com/S40911120/recensa/tree/aee7df884284b0f3656385a9c3bb6525fd9f5519),
[cc-dm](https://github.com/gitrishiom/claude-code-dm/tree/5012841e0af8fb6a56bd19373dbc4bb93a0e5640),
and [Claude Relay](https://github.com/gvorwaller/claude-relay/tree/573d1963e719cc317ade100d573394ba00a77839).
The useful mechanisms include incremental transcript reads, session/modal
rechecks, and distinguishing context insertion from later acknowledgment.
None of the inspected projects establishes the full accepted Desktop contract
by adoption alone. Their [source-level comparison](2026-10-01-observer-scope-review/survey-followup.md)
separates transferable ideas from proposed dependencies; no dependency was adopted.

Two particularly concrete leads deserve follow-up. A documented `MessageDisplay`
hook might observe an explicit assistant ACK without raw JSONL parsing, but it
is not an incoming-peer delivery witness and Desktop support needs verification.
A selected SDK session reader might provide positive transcript evidence without
an app observer, but it exposes stored messages, not every live setting. The
[native field comparison](2026-10-01-observer-scope-review/native-followup.md)
records which proposed hooks each might replace and where it cannot yet do so.

### Fixture identity is also a scope tradeoff

The current procedure permits reading one already selected metadata file and
forbids directory discovery across other tasks. Its filename depends on account,
organization, user-data root, and Desktop task identifiers that have not all
been acquired. The receipt solves that circularity by adding app hooks.

A bounded identity-discovery read or an existing UI event may avoid the receipt.
That requires deciding the exact additional fields or directory entries that
may be inspected and proving which record belongs to the newly created fixture.
The [targeted source check](2026-10-01-observer-scope-review/native-source-delta.md)
confirms that existing renderer paths expose a Desktop task ID in specific
branches, but establishes no external read-only accessor. The Desktop metadata
filename uses that Desktop ID; the Code ID can come from its contents for later
transcript binding. Requiring the Code ID merely to name that file would add a
false prerequisite. Choosing the newest file is not sufficient binding. Broader discovery is a
possible read-scope change, not an unavailable filesystem capability and not
a grant supplied by this review. It also leaves the separate effective-state
observation problem intact.

## Recommendation and the next decision

Keep the direct native MCP sender as the leading candidate. Do not add a
model-driven sender session or implement a new socket protocol without evidence
that it solves a specific remaining problem.

Before resuming the receipt or archive work, compare the narrowest existing
reader and observation combination field by field. Name each producer, its
freshness and applied-versus-saved meaning, exact-task binding, required access,
and the missing fact. Test the assumption that an app adapter is needed, rather
than treating an absent external accessor in one survey as proof of necessity.
Any later live check must be separately scoped to a disposable peer.

An instrumented experiment also needs an explicit target claim: whether it
qualifies a permanently modified operating route, or merely measures behavior
intended for unmodified Desktop. A modified-build observation does not itself
qualify the restored build. Source comparison, observation effects, and relevant
unmodified-runtime evidence must support any transfer of findings.

The next operator decision is among a smaller existing-surface route, a clearly
bounded residual observer for specific missing fields, or an explicit change to
the qualification claim if complete evidence is impractical. This review does
not silently narrow the accepted claim or choose installation. The receipt's
source direction and 15-minute ceiling remain conditional on that route choice.

## Evidence and review method

The [research method](2026-10-01-observer-scope-review/method.md) records fresh
first-round contexts, permitted inputs, frozen report identities, exchange,
independent critique, follow-up, and source verification. Initial errors remain
in the captured first-round reports and are corrected in follow-ups and this
synthesis. The coordinator owns publication and the native tracker graph.

The source audit rechecked all eight build-input digests and all ten patch-anchor
occurrences against the retained pristine manager. All matched. It did not
rebuild the archive, rerun its historical tests, or launch the candidate. Public documentation about current Linux support does not qualify that inspected
package or establish that every documented hook is present in its selected
executor. This
review compares architecture and evidence; it supplies no new security
acceptance or live authorization.
