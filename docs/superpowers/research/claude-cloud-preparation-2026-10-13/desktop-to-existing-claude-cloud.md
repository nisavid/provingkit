# Claude Desktop-hosted Code to an existing Claude Cloud task: independent source/design preparation

The exact-ID CLI and browser SSE client are partial candidates. Neither establishes this Desktop caller's access, an independent Cloud result reader, or validated fulfillment. Browser query initialization writes controls, and its POST uploader retries without an established server deduplication contract. Those effects need resolution before live selection.

## Scope and identities

I applied research, prototype's logic/design branch, and capturing-agent-procedures under the frozen read-only override: no delegation, acquisition, SDK/CLI execution, edits, Git/forge/browser actions, private reads, authentication, prompts, sends, installation, restart, or provider work. No sibling preparation report or prototype was read. This is an independently frozen initial source handback; no synthetic test or live operation ran.

The four controls were read first. Request SHA-256 is c1c66059e2a95d6ee990b48d7db46fb749b5012a3bc5c64e987ae24c845bcfa5; plan is 217097d4e99c00a3ebcf4dd4f1760f10c3cd9b8a5123d9c60a0359a3c2301443. Selection is 3546412d8e049d8d357856f4095b95fb67c220cb0b211a6111f6802440086c22; freeze is 5a06fa02a908c4ff60866571c7e12df75e2b8ad98dd0e750d7d4614a30380599. All 23 literal pinned inputs matched their lengths and digests before and after examination. No nested manifest was expanded.

The registry observation dated 2026-10-13T12:18:47Z reports latest 0.3.296. Four complete versioned exported bodies acquired October 13 total 1,442,797 bytes; the separate October 12 main SDK bodies total 1,777,704 bytes. These are known public-source footprints, not installed runtime, distribution-integrity, or workflow-cost evidence. The dated FIRST inventory is interpreted with its October 11 addendum taking precedence. Context7's admitted output covers MCP SSE and session storage; it supplies no browser-to-Cloud binding.

Installed skill readings were research/SKILL.md (985569f15739c713d6784887c3d186d4ef9ac85bec5ad9c068d25bf0739928e4), prototype/SKILL.md (714de632d116bb73f65cdb5a882db15b9369a6713b9a47c0fad827848f0bfbe3), prototype/LOGIC.md (f61c7d249e786a79ef289018901c348271e1798dd0b0bc5607b5c6f4d4a01ab9), capturing-agent-procedures/SKILL.md (b9f13f1b78c338383253c1c89c79172d5f5e938757311c97569520e2ac6c7554), and its references/producing.md (2b93c88913230144b3d5e9fdd9e2efe3371332ded45e40e523813c2550e84bb1). These are end-read identities, not pre/post pinned-skill attestations.

## Caller and population boundaries

The selected sender is a particular Claude Desktop-hosted Code session. Its actual exposed command or external MCP tool, execution host, local/SSH/WSL namespace, reachable controller, and returned-output path remain unknown. Main SDK query/spawn/MCP declarations and this Codex worker's tools establish none of that exposure. Desktop's query account and a controller host's accepted credentials/account route are separate bindings.

The target is an exact existing Cloud task, not an SDK-owned replacement, a native local UUID transcript, or a Remote Control web view of local execution. Record requested target, resolved Cloud ID/URL, actual worker/session, execution location, ownership, caller access, account route, and credential acceptance separately. This packet supplies no actual target or account observation.

The operation contract requires correlated receiver receipt for notification, caller-validated output for work, independently observable addressability for creation, status and result inspection separately, later correlated reply after the call ends, and same-task context for continuation. No route here has full qualified coverage.

For the existing-task profile, the following assessment is conditional source coverage. P means a partial mechanism, ? an unestablished capability, U unsuitable for this population/purpose, and – inapplicable. Inspection shows status/result separately.

| Candidate or supporting subroute | Notify | Work | Create | Inspect | Later reply | Continue | Population limit |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Exact-ID Cloud CLI | P | P | – | ?/? | ? | P | Authorized existing Cloud ID; queues input |
| Cloud UI independent reader | – | – | – | P/P | ? | – | Human conversation/diff route; automated access unknown |
| Browser SSE query | P | P | – | P/P | ? | P | Correctly bound CCR session; active client; partial streamed return, later sender route unknown |
| Raw SSE GET / REST event-list reader proposal | – | – | – | ?/? | – | – | No standalone reader/server contract established |
| Legacy browser WebSocket query | P | P | – | P/P | ? | P | Bound legacy remote session; no SSE helpers; partial streamed return, later sender route unknown |
| Native ListAgents/SendMessage | P | P | – | P/? | P | P | Eligible discovered peers; Cloud discovery/auth/return connection unknown |
| External MCP entrance / raw inbox socket | ? | ? | – | ?/? | ? | ? | Current MCP peer schema unknown; socket contract incomplete |
| Desktop tab tools | U | U | – | U/U | U | U | Documented eligible local/SSH/WSL app tabs exclude Cloud |
| Main SDK query/resume | U | U | – | U/U | U | U | Own process/stored session; no arbitrary held Cloud attach |
| Main SDK transcript/store readers | – | – | – | U/U | – | – | Native UUID storage; selected Cloud mapping absent |
| Worker bridge attach | U | U | – | U/U | U | U | Registration/worker state ownership, not passive reader |
| Teleport / Remote Control | U | U | – | U/U | U | U | Replacement local continuation / local execution |

Cloud CLI creation, Cloud UI creation, bridge createCodeSession, main SDK creation, and Routine trigger are separately declared controlled/new-task lifecycles. Their source-shaped creation calls do not prove addressability, actual execution, or access from this caller. Bridge-owned workers retain partial input/status/output/synchronous-return/continuation declarations; those cannot transfer to an independently owned Cloud task. Native peer messaging remains a distinct retained alternative, not evidence or authority for the CLI/browser work request.

## Owning interfaces and source findings

CLI behavior is attributed to retained-public/2026-10-10-peer-portfolio-claude.md lines 58–60 and the October 11 addendum's Cloud section, citing https://code.claude.com/docs/en/claude-code-on-the-web#send-follow-ups-from-the-cli. The reported form is claude -p MESSAGE --cloud SESSION_ID --output-format json, accepting ID or URL and returning {ok, session_id, url} on success. It queues and exits without waiting; some configuration failures use stderr without JSON. No CLI implementation body is admitted. Sender exit/ok does not establish receiver receipt, execution, result, peer origin, or safe retry. An independent reader is a mandatory component class whose deployment is unresolved.

Direct browser source: https://unpkg.com/@anthropic-ai/claude-agent-sdk@0.3.296/browser-sdk.d.ts and https://unpkg.com/@anthropic-ai/claude-agent-sdk@0.3.296/browser-sdk.js. Coordinates below use one-based source lines and, for minified code, zero-based decoded-text character offsets.

SSEOptions (declarations lines 27–76) names streamUrl, sendUrl, required sessionId, shared headers, fromSequenceNum, truncation callback, and delivery callback. Example endpoint shapes are /v1/code/sessions/{id}/events/stream and /events. Authorization and anthropic-client-platform are declared header names; neither accepted credentials nor client-platform values are established.

Exported query is WTe (JS line 153, approximately chars 1385537–1386580). It creates qm for SSE or mk for WebSocket, constructs If/Query, and starts streamInput. If's constructor starts readMessages and initialize immediately (line 49, chars 820570–820900). initialize builds and sends a control_request (line 51, chars 831992–834600); request assigns a request_id and writes it (chars 843361 onward). Hooks, SDK MCP manifests/configuration, schema, prompt suggestions, and permission/dialog handling are control-bearing options. Empty prompt input still initializes. streamInput waits for the initialize write barrier, not necessarily the initialize response, then writes prompts (line 53, char 849483 onward). No passive attachment or harmless concurrent-client behavior follows.

qm connects with GET, supplied headers, Accept: text/event-stream, and Last-Event-ID from its internal cursor (line 146, chars 1228133 onward). It consumes durable client_event and selected ephemeral_event frames. Durable envelopes come from event_id, sequence_num, created_at, and source in the delivering frame. getCcrEvent uses a WeakMap keyed by the exact yielded message; copying it loses the lookup. Payload ccr_event is stripped. Event source is server-channel provenance under the declared endpoint, not authenticated native peer identity or grant authority.

The source gates worker-output-shaped user frames, rejects malformed content, drops non-worker result/assistant types, and guards replies to issued control request IDs (chars 1230200–1232550; helper predicates lines 144–145). These are client filters, not a complete hostile-server security claim. Unknown or malformed frames are counted; counters provide categories, not recovery of contents.

The public cursor covers durable messages actually yielded, advanced by readSdkMessages immediately before yield (line 51, char 831856). The internal wire cursor advances even for dropped/consumed events (line 146, qm.advanceCursor/readStream). Nonconsecutive yielded sequences therefore do not alone prove loss. getSseLastSequenceNum excludes buffered/unseen messages and internally consumed controls. catch_up_truncated continues from a later point and calls a contained handler; the client does not recover the REST gap. No REST-list implementation or accepted read contract is supplied.

delivery_update carries event_id/status/timestamp and is not replayed. The declarations describe RECEIVED, PROCESSING, and PROCESSED; unknown strings remain informational. Durable input echo maps an SDK payload UUID/correlation to event_id; delivery updates join by event_id. PROCESSED describes a turn ending, not semantic acceptance or fulfillment. SDK result identity/UUID is distinct from event ID, sequence, and caller correlation.

Query readMessages consumes controls internally and yields result messages (line 49, char 822524 onward). Direct main declarations at https://unpkg.com/@anthropic-ai/claude-agent-sdk@0.3.296/sdk.d.ts, lines 5785–5885, describe subtype, is_error, result, user_message_uuid(s), session_id, result_index, usage, and optional structured_output. Require matching session, relevant input UUID(s), fresh correlation, correct result kind, completeness, and declared semantic checks. A successful subtype can carry is_error; historical replay, unrelated concurrent turns, partial assistant text, and model-less empty results cannot silently satisfy the work.

## Retry, reconnect, and bridge effects

Browser qm uses 15-second connect and 45-second liveness defaults, exponential reconnect delay with 1-second base/30-second cap, and five consecutive reconnect attempts (line 146, constants and handleStreamEnd). A successful connect resets that budget, so it is not a whole-workflow bound. HTTP 401/403/404 close permanently. Reconnect does not refresh credentials, recover truncation, or replay delivery updates. Replacement query reinitializes and can write again.

write adds a UUID when absent, then awaits uploader enqueue, not confirmed POST or worker receipt (chars 1233969 onward). postOnce sends {session_id, events:[{payload}]} with a 30-second request timeout. It discards successful response content. Other HTTP errors become retryable uploader errors, with numeric Retry-After handling; network/timeout errors also reach uploader retry.

Y1.enqueue/drain (line 111, chars 1204527 and 1209500 onward) retain and resend the same queued payload after failure, using 1-second base/30-second cap plus jitter. Three consecutive failures drop a batch; qm supplies no onBatchDropped reporting callback. Permanent transport close stops retries. The same UUID survives internal retries, but no admitted server body establishes idempotency, deduplication scope/retention, or non-submission. Enqueue resolution and dropped writes can therefore lack reliable completion evidence. The frozen operation contract requires reconciliation after possible submission; this implementation's automatic ambiguous-failure retry is a concrete unresolved selection issue.

Legacy mk (line 146, char 1236953 onward) opens globalThis.WebSocket(url), optionally sends OAuth authMessage, sends 50-second keepalives, parses newline messages, and strips payload ccr_event. Its supplied headers option is not used by this constructor. No SSE durable envelopes, drop/cursor helpers, or transparent reconnect is implemented in this class. SSE guarantees must not transfer to it.

Direct bridge declarations: https://unpkg.com/@anthropic-ai/claude-agent-sdk@0.3.296/bridge.d.ts, lines 31–94, 96–246, 248–290, and 374–418. fetchRemoteCredentials POSTs /sessions/{id}/bridge and bumps worker_epoch; malformed 2xx may already have registered. attachBridgeSession registers when epoch is omitted; reconnect can reuse an epoch. The handle writes messages/results/permissions, reports state/metadata/delivery, flushes, and closes. outboundOnly suppresses inbound SSE; it is not passive. createCodeSession creates a new CCR session. bridge.mjs/server registration bodies are absent, so these remain their own lifecycle declarations.

Main SDK source https://unpkg.com/@anthropic-ai/claude-agent-sdk@0.3.296/sdk.mjs exports lWe/query (line 143, char 1218234), creates its process transport, passes --resume/--fork-session, and calls custom spawnClaudeCodeProcess or spawnLocalProcess (line 136, chars 1145581/1147820). nIt/getSessionMessages chooses store or FN transcript reader (line 145, char 1231375; FN line 110, char 523515); rIt/listSessions chooses store or filesystem readers. Declarations lines 895–931 and 1082–1110 describe JSONL chain/history and directory scope. These support stored-history components, not a Cloud result reader or actual Desktop installation.

## Proposed finite design and later checks

Propose a pure evidence reducer with separate submission, receipt, acceptance, execution, output, validation, inspection completeness, and continuation fields. Events carry profile, requested/resolved IDs, source/time, transport outcome, input UUID, envelope event ID/sequence/source, delivery state, result UUID/input references, gaps, and validation verdict. Keep queued/held/refused/stale/incomplete/unknown without erasing earlier milestones. Possible submission enters unknown and disables resend pending reconciliation; processed advances only execution evidence. Fulfillment requires bound complete output passing caller checks. A result arriving after the sender exits remains inspectable evidence; later reply additionally needs a bound return path.

Use the same invented task for each candidate: correlation desktop-cloud-example-1; read the supplied synthetic rows {name: cedar,value:2} and {name: birch,value:3}; return their names alphabetically and total 5, without editing. Caller checks exact correlation, birch/cedar order, integer 5, exact task/input binding, and complete result. A textual no-edit claim is not preservation evidence; later approved before/after fixture observations would check it.

Proposed public TDD boundary, pending agreement: feed finite typed evidence records into the pure reducer/validator and observe milestone/outcome decisions. Cases include CLI exit without receipt, correct result, wrong target/input/correlation, is_error success, historical result, merged inputs, forged payload envelope, lost delivery update, truncation, buffered break, possible submission, internal retry/drop, stale credentials, and replacement identity. These would prove constructed handling only. No code, HTML prototype, or tests were added or run.

Smallest later sequence: identify the selected Desktop caller's exposed command/MCP and actual host namespace without sending; bind an approved exact Cloud fixture, account/controller route, and independent result reader; settle initialization/concurrent effects and POST deduplication/reconciliation; review the exact prompt, reader scope, limits, and restoration; obtain separate fixture and operation grants; run one bounded no-edit request with receiver/result evidence. Idle/busy and failure/recovery remain separately scoped. Basic live work retains the thirty-active-minute reassessment boundary; it is never completion by timeout.

Source examination used no new public acquisition or provider call. Worker effort, total prior acquisition/review effort, credential setup, private bytes, polling, quota, provider usage, cleanup, and total workflow cost remain unmeasured. SDK usage fields are estimates and can be cumulative; they are not complete controller/reader/review costs.

## Procedure consumption and handback

I loaded the admitted updating-cross-harness-catalog source associated with 701af, plus its README/format. Procedure digest is 1ef2b637752bb28fd277d6f7bb75c951ec56bc9fd69af89b8f09f3aeb760e0a4. Trigger: reconciliation of this coherent producer batch. Required producer result: these frozen source findings, component crosswalk, operation limits, caller gaps, and proposed checks. No catalog read/update, regeneration, review, publication, installation, or consumer reaction is claimed.

The common comparison/reaction join in #569 owns reconciliation with #552, current catalog state, generated views, independent review, publication, and Ivan's actual reaction. Current reaction is not supplied. Preserve distinct CLI actuator plus unresolved independent reader, active SSE client plus unresolved REST gap reader, legacy WebSocket, native alternative, and worker bridge lifecycle. The reusable correction proposal is to make active initialization and ambiguous automatic write retries explicit selection gates while keeping caller access independent from shared receiver-source findings. Capturing and downstream invocation remain pending with the coordinator.
