# Receiver evidence with an exact-file reader and a Stop hook

The reader and Stop projection now provide runnable source experiments for
receiver evidence. Static inspection also connects native socket addressing,
incoming-message records, hook dispatch, and several runtime-state getters in
the Code release target embedded in Desktop. These findings make a bounded
fixture experiment more concrete. They do not establish the selected live
executor, authenticated delivery, or full runtime preservation.

This report reconciles [Build bounded reader and hook evidence prototypes](https://github.com/nisavid/provingkit/issues/393),
[Establish bounded fixture discovery and executor binding](https://github.com/nisavid/provingkit/issues/394),
and [Identify missing receiver runtime-state producers](https://github.com/nisavid/provingkit/issues/395).
The [component decision](https://github.com/nisavid/provingkit/issues/388#issuecomment-5961209463)
is the controlling contract. Full actual-state snapshots apply to qualification
and affected requalification. Ordinary sends retain fresh peer and consent
checks, receiver-origin delivery, and a distinct correlated acknowledgment.

## Evidence and source identity

The two research workers independently froze first reports, then independently
inspected a newly acquired public engine artifact. After the first prototype
was frozen, they exchanged reports and challenged the prototype. The coordinator
implemented the prototype and received research findings during that work; it
was not a third independent research lane. The
[source archive](2026-10-02-reader-hook-sources/README.md) preserves the original
reports and subsequent reconciliation. This report gives the current conclusions;
the first reports retain the uncertainty present when they were written.

| Source | Identity |
| --- | --- |
| Retained Desktop | 2.9939.4; commit `a166d8a7c640e65ad825ebfb99d74ccbb9c8940d` |
| Embedded Code target | 2.1.284; commit `16cbb4ddeeb473f57fd8d5b713764903d7928e66` |
| Declared Desktop SDK wrapper | `0.3.284-rc.20260927.t043816.sha16cbb4d` |
| Public stable SDK examined separately | 0.3.284; member SHA-256 `32d062c37b03e10870fbf839f54694545ee01bc0ec719e47078fbed76e30ef71` |
| Public target archive | 85,295,282 bytes; SHA-256 `20b1b16df81e34abc68bef87c5a8433106f0cf4e84b2dd507e37bb7978cbd6f2` |
| Decompressed engine | 243,059,896 bytes; SHA-256 `dee301c3e248c62137cc15aafc2781bd5316c66720dd890d72e0054a024ce7d9` |

The [public RC archive](https://downloads.claude.ai/claude-code-releases/rc/16cbb4ddeeb473f57fd8d5b713764903d7928e66/2.1.284/linux-x64/claude.zst)
was downloaded on 2026-10-02 and matched Desktop's embedded compressed digest.
Its embedded version and commit agree. The binary was retained without execute
permission and inspected as data; it was never launched, imported, or installed.
The stable SDK is not a demonstrated byte match to Desktop's RC wrapper.
Desktop permits overrides, preseeds, pins, fallback versions, and launcher
transformations, so this remains a source-target match.

The archived reports identify retained Desktop members by digest and use
zero-based byte spans. No vendor binary or full Desktop source is published
with this report.

## Fixture identity and the native destination

Desktop's metadata serializer persists its `sessionId`, current `cliSessionId`,
and prior Code lineage. Initialization connects a Code-reported session to the
Desktop record. It does **not** serialize `unarchivedCliSessionId`; that field
is in-memory state. A file reader must not depend on it.

The native engine binds its inbox, exports the actual socket path through
`CLAUDE_CODE_MESSAGING_SOCKET`, and supplies a connected address encoder/parser
and SendMessage path. The selector is `uds:` plus an encoded path. Literal
percent signs and other encoded characters rule out arbitrary string prefixing.
The native sender accepts that decoded endpoint. This closes the source-level
address-conversion question.

The selected-task witness remains missing. An internal `LocalSessions.start`
return identifies a task inside the app, but no external attach endpoint was
established. A plausible later witness is a unique, agreed setup response in
the operator-selected fixture, observed by an authorized Stop collector with
Code ID and socket, then joined to exactly one selected metadata record's
current Code ID. A host-session label could corroborate the association; it
does not establish operator selection or consent. Historical IDs alone do not
admit a current peer.

The research proposes one bound account/organization metadata directory, a
nonrecursive listing capped at 128 entries plus one overflow entry, at most
three operator-selected metadata files, and at most 1 MiB plus one overflow
byte per file. These numeric limits are proposals for the next decision.
The grant would cover whole serialized files, including nested settings,
titles, reminders, grants, summaries, errors, and other private fields.
Projection afterward does not narrow acquisition.

Native `ListAgents` is not an exact-file alternative: its implementation reads
registry records, checks processes and sockets, and can clean up stale records.
Its formatted public result does not expose every structured identity. Its
declared read-only classification does not prove absence of housekeeping writes.
Likewise, optional expected-process checks in the transport are not supplied
by every inspected ordinary SendMessage call. These are source facts to assess
in a later plan, not accepted identity controls.

See the [identity first report](2026-10-02-reader-hook-sources/identity-first.md)
and [engine supplement](2026-10-02-reader-hook-sources/identity-engine.md) for
serializer, binding, encoding, discovery, and send call paths.

## What the prototypes supply

Open the [interactive demonstration](../prototypes/receiver-evidence/demo.html)
and its [contract](../prototypes/receiver-evidence/contract.md). The browser
uses the same pure functions as the tests and only invented input.

| Component | Useful result | Limit |
| --- | --- | --- |
| Explicit-file acquisition | Reads the two supplied files with a limit-plus-one bound; records bytes read and EOF completion | No discovery, coherent-snapshot claim, writer-completion proof, or hostile-path containment claim |
| Record interpreter | Selected-session notice and response candidates, exact specimen text, timestamps, ordering, selected origin fields, and gaps | A deliberately narrow selected-record schema, not a complete native session reader or authenticated receiver evidence |
| Stop projector | Exact match against the normalized final-text field, Code identity, optional cwd/mode, capture interval, and gaps | Pure event projection; no installed hook, stdin reader, sink, socket/environment observation, or full-state snapshot |

Cross-examination found and corrected a native-schema mismatch in the first
reader. Cross-session origin uses `from`, optional host-openable `fromSession`,
`msg_id`, and decoded `body`; `senderTaskId` describes an in-process background
subagent. Native UDS input is queued and persisted with `isMeta:true`.
The revised reader admits peer user metadata, rejects metadata responses, uses
the decoded body, and never guesses a missing body by stripping an envelope.
It retains the recorded connecting PID when present. A sender address is
sender-asserted, and a connecting PID can identify a relay and can be recycled.
All results therefore retain unqualified sender authentication.

The source chain is explicit: the RC peer schema is at bytes
`[199623000,199627050)`, receive/queue at `[221431000,221432900)`, headless
forwarding at `[221007150,221009550)`, user-record construction at
`[213089150,213090300)` and `[208923600,208925500)`, and persistence at
`[209117400,209119500)` and `[209129150,209130050)`. Actual fixture records remain
unobserved.

Stop chooses the last assistant record's text blocks, joins them with newlines,
trims them, and omits an empty result. This is not raw transcript equivalence or
proof that the text is an intentional ACK. Its producer and command dispatch
are connected in source, but settings, trust, matching configuration, and
cancellation can prevent execution. Receipt time cannot date text production;
the projector keeps that gap even for a recent capture. Complete hook input can
include background-task descriptions and commands and cron prompts before any
projection discards them. The [proposed operation](../prototypes/receiver-evidence/README.md#proposed-hook-operation-to-assess-later)
names the configuration, exposure, retention, and cleanup questions still needed.

The tests cover mismatches, incomplete records, stale timing, ordering, quoted
text, optional fields, collector interruptions, native-origin specimen fields,
and bounded file reads. They establish synthetic behavior only. No absence
result becomes held, refused, or proof of nondelivery; none causes a resend.

## Runtime-state producers and gaps

The new engine artifact resolves the first report's missing-handler question.
It also shows exactly why the getters do not yet complete the preservation claim.

| Required observation | Source contribution | Remaining gap |
| --- | --- | --- |
| Authenticated running account | Status and initialization project credential selection and local profile metadata | Neither establishes which account an inference request authenticated; SDK `accountInfo()` is cached initialization |
| Actual model | Settings `applied`, status, and context usage expose configured/resolved session values; fallback events expose some attempt changes | These meanings differ. A fallback can change an attempt without changing session getters or `PostModelSwitch` |
| Active permission mode | Stop can supply event-time mode; engine and host setters/events carry partial state | Status passes mode to an enabled/disabled display row, not a raw mode field; endpoint and pending-change coverage remain incomplete |
| Applied Code rules and directories | `list_permission_rules` reads current `toolPermissionContext`, applicable allow/ask/deny arrays, sources, and additional directories | Does not supply all runtime flags, host grants, or pending mutations |
| Effective Desktop permissions | Existing broker records, browser evaluator, and computer-use evaluators supply additional facets | Time-dependent grant expiry and contextual inputs matter; no complete aggregate producer is established |
| Current cwd | Status invokes the engine cwd resolver and formats its result | Resolver can fall back to original cwd on error; formatted output is not a complete raw cwd/worktree observation |
| Registered worktree | Desktop's registered-worktree resolution and lifecycle events | Separate from arbitrary current cwd, pending moves, and selected query binding |
| Sample identity and timing | Query transport correlates control replies | No atomic aggregate snapshot; require per-field intervals and before/after receiver/query/lifecycle checks |

`list_permission_rules` handlers and builder are at RC bytes
`[221226535,221226950)` and `[231927050,231928958)`; named settings `applied`
values at `[221225050,221226050)`; status construction at
`[232758900,232759575)` and cwd resolution at `[198480300,198481700)`.
Some control requests reject selected connection types. Their implementation
does not prove access through the chosen Desktop query.

StatusLine is not an established cheaper headless producer in this artifact.
The traced constructor/subscription belongs to the React UI, and the headless
adapter has no status row. Adding a logger would not make that producer exist.
The [state first report](2026-10-02-reader-hook-sources/state-first.md) and
[engine supplement](2026-10-02-reader-hook-sources/state-engine.md) contain
producer paths, timing, pending-change distinctions, and artifact limits.

Temporary app observation remains a candidate for exposing the selected query
and host evaluators. It cannot turn cached or incomplete fields into complete
evidence. If selected, its installation, interruption, restoration, and transfer
of results to ordinary Desktop must be assessed for the particular missing
producer. No recurring app dependency or new patch is selected here.

## What the comparison must decide next

The [comparison join](https://github.com/nisavid/provingkit/issues/396) should
consume this revision, the prototype contract, the frozen cross-examination,
and the final review. It should separate two possible next increments:

1. A bounded, separately authorized no-send fixture check could test actual
   selected-executor identity, hook configuration/loading, Stop output, and
   independent Desktop/Code/socket binding. It would not qualify delivery or
   full-state preservation.
2. Further source design could target authenticated account evidence, actual
   model interpretation, effective permission completeness, and access to the
   selected query. App observation is justified only where it supplies a named
   missing producer or access path.

The [experiment decision](https://github.com/nisavid/provingkit/issues/397)
owns the operator's prototype reaction and choice. Probe preparation remains
blocked by that decision. No private receiver read, hook activation,
installation, task creation, restart, prompt, or notification follows from this
source increment. The old receipt's 15-minute deadline applies only if that
procedure is selected again.

## Method captured for consumers

Use `capturing-agent-procedures` when carrying this method into a maintained
tool: bind every source artifact, distinguish source target from actual
executor, trace producer through forwarding and persistence, freeze independent
first findings, cross-examine, repair source/schema mismatches, and review the
reconciled candidate. Load this report and the prototype contract before
dependent design; record the revision used. A new build is unassessed rather
than incompatible, with prior evidence retained when graduated checks justify it.

This is a proposal and a source experiment outside installed Rolecasting.
Broader workflow codification stays with
[Define, implement, and evaluate reusable agent-panel workflows](https://github.com/nisavid/provingkit/issues/306).
