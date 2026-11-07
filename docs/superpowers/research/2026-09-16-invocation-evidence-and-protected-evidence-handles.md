# Invocation evidence and protected-evidence handles

Status: public-source research for
[`nisavid/provingkit#43`](https://github.com/nisavid/provingkit/issues/43),
observed 2026-09-16. This report is decision input for
[`nisavid/provingkit#8`](https://github.com/nisavid/provingkit/issues/8). It is
not qualification evidence, a provider or infrastructure selection, an
implementation contract, or authority to invoke a harness, handle credentials,
sign, publish, release, or mutate a host.

## Finding

None of the surveyed public interfaces produces a publicly verifiable statement
that binds one selected-harness invocation to the full Rolecasting and
Tricritical field set. OpenAI's Compliance Logs Platform is the only surveyed
interface with documented product-authenticated readback: a scoped Admin API
lists and downloads immutable `CODEX_LOG` JSONL files for normalized clients.
The schema's normalized-client enum includes `CODEX_CLI` and the distinct
desktop identifiers `CODEX_DESKTOP_APP` and `CODEX_CHATGPT_DESKTOP`; it does not
define which desktop identifier this selected surface emits. Prompt and response
events carry stable event IDs, session and optional turn/call IDs, model, status,
and product context. Delivery is at least once, files expire after 30 days, and
readback uses a short-lived signed download URL. Required file metadata includes
`file_sha256`, a SHA-256 digest of the complete file contents for integrity
checking. The interface exports no event/file signature or public verification
key and does not bind exact candidate bytes or the complete effective-authority
chain. [OAI-D6]

The remaining strongest interfaces expose useful local correlation and
lifecycle evidence:

- Codex app-server v2 exposes thread and turn identities, submitted input,
  configured model, product source and version, status, items, and local
  history readback. Its own source says the thread's configured model is not
  per-turn execution telemetry. [OAI-S2]
- Claude Code headless output and Agent SDK messages expose session, message,
  result, model-usage, error, and retry facts, with local session persistence
  and resume. [ANT-D1] [ANT-D3] [ANT-S1]
- Cursor desktop hooks expose a conversation identity, per-prompt generation
  identity, configured model, product version, prompts, tool lifecycle, final
  response, and an optional local transcript path. Cursor Agent CLI exposes a
  separate JSON/JSONL session, tool-call, result, and optional request-ID
  surface. [CUR-D1] [CUR-D2]

Except for the Compliance Logs Platform fields within its stated coverage,
those values are native logs, local protocol fields, or controller
observations. No reviewed interface specifies a per-event signature or MAC, a
portable product-issued receipt, or exported public verification material. A
controller can bind the raw bytes it sees into a later record, but that record
would attest to the controller's observation—not independently prove what the
product or upstream model service executed. A Compliance consumer can retain the
authenticated file metadata, verify the downloaded bytes against `file_sha256`,
and sign that metadata and verified digest as the controller's own observation.
Detached file bytes and their hash do not retain OpenAI-authenticated origin by
themselves: the schema supplies no portable OpenAI signature or key over the
file, metadata, or events.

No selected interface returns a value-free protected-evidence handle with
documented confidentiality, stable lookup, authenticated readback, retention,
and access semantics. The initial and freshly revalidated Codex app-server
source contains the nearest
transport-shaped primitive: a thread attachment has a stable thread-local
identity, type, key, arbitrary JSON payload, creation time, idempotent add, and
paginated list. That API neither gives the payload evidence semantics nor
protects or authenticates it, and it is absent from the two historical Codex
release tags checked here. [OAI-S3]

## Scope and method

The selected surfaces are ChatGPT desktop Codex mode, Codex CLI/TUI, Claude
Code, Claude Desktop, Cursor desktop, and Cursor Agent CLI. The study reviewed
primary moving documentation dated 2026-09-16 and immutable public vendor
source. Correction revalidation at 2026-09-17T03:46:16Z refetched the cited
unauthenticated public sources. Every immutable source file still matched its
recorded digest. All directly retrievable moving-document bodies changed, while
bounded checks confirmed the cited interface facts still appear. The Admin
schema advanced from 2.5.20 to 2.5.21; its version history attributes that
change to Codex analytics documentation, and the Compliance checksum and client
enum facts used here remain present. OpenAI Help and Admin endpoints still
returned 403 to direct `curl`; current Help content and Admin schema fields were
rechecked through public indexed retrieval, and those fresh bytes are not
described as recovered historical captures. The accompanying
`docs/superpowers/research/2026-09-16-invocation-evidence-public-source-manifest.json`
records the historical captures, fresh retrieval provenance, revisions, body
digests where obtainable, and explicit no-digest limits for indexed retrieval.

The frozen issue and decision inputs were verified byte-for-byte against input
manifest SHA-256
`2366ff995e88ae13529a63707398c0f272adea6394c9d466ee3d25bdd214efc4`.
Context7 results for `/openai/codex`, `/websites/code_claude`, and
`/websites/cursor_cli` were used only as locators; every resulting claim below
was checked against an owning primary page or public source revision.

No harness was invoked. No inference, account or credential inspection, local
client inspection, host inspection, signing, provider call, or sensitive sample
collection was performed. The 2026-09-07 host inventory is historical document
evidence only. Its observed versions do not establish current host state or
live capability.

Accepted #8 decisions
[Q1–Q6](https://github.com/nisavid/provingkit/issues/8#issuecomment-5565178275),
[Q7–Q10](https://github.com/nisavid/provingkit/issues/8#issuecomment-5567698314),
and [Q11](https://github.com/nisavid/provingkit/issues/8#issuecomment-5568191158)
remain fixed. In particular, the comparison does
not promote useful-but-weaker review evidence into production evidence, does
not infer exactly-once behavior, keeps raw protected evidence out of portable
receipts, preserves linked immutable attempts, and does not substitute a local
log or package checksum for the asymmetric product/producer authority required
by Q11.

### Classification rubric

Every field in every candidate table has exactly one classification:

- **D — documentary:** an official document describes the behavior or UI, but
  the interface does not emit an invocation-bound value for this field.
- **P — pinned-source:** an exact public source revision defines the field or
  behavior. This is not evidence that a distributed build or invocation had it.
- **C — controller-observable:** the documented interface supplies the value to
  its local caller or hook. The value has no documented independent product
  authentication.
- **A — product-authenticated:** the product supplies an invocation-bound value
  through documented scoped authenticated readback or a verifiable signed
  statement. The table must state which one. Authenticated readback at retrieval
  time is not automatically portable or publicly verifiable afterward.
- **U — expressly unsupported:** the owner explicitly says the field or
  interface is unavailable on that surface.
- **? — unknown:** the primary-source set did not establish the fact. This does
  not assert impossibility.

`C` is intentionally stronger than a UI description and weaker than `A`.
Normal client authentication or protected transport can authenticate access to
a service without creating a durable invocation statement; it is not upgraded
to `A` by itself. Compliance `CODEX_LOG` fields qualify because the owning
product documents a scoped readback API and immutable files, but only within
that API's stated retention and transport boundary.

## Cross-surface result

| Surface | Evidenced candidate interfaces | Best correlation | Model evidence | Result/readback | Product-authenticated receipt |
| --- | --- | --- | --- | --- | --- |
| ChatGPT desktop Codex mode | App UI/history; Compliance `CODEX_LOG` for covered workspace use | Compliance event/session/optional turn/call IDs; UI alone is documentary | Compliance response model; UI/default selection | Scoped immutable, checksum-verifiable log-file readback; UI/history | Authenticated readback and whole-file integrity, not a portable signature |
| Codex CLI/TUI | Compliance `CODEX_LOG` for covered workspace use; `codex exec --json`; app-server v2; lifecycle hooks | Compliance event/session/optional turn/call IDs; local thread/turn/hook IDs | Compliance response model; local selection/configuration fields | Scoped immutable, checksum-verifiable log-file readback; local JSONL/history/transcript | Authenticated readback and whole-file integrity, not a portable signature |
| Claude Code | `claude -p` JSON/stream JSON; Agent SDK stream; hooks | Session ID, message UUID/ID, tool IDs | Assistant message and model-usage fields | Result messages, API retry events, persisted local sessions | None found |
| Claude Desktop | Code-tab UI and shared Claude Code hooks | Hook session ID | UI selection and session-start model | Interactive transcript; no `--print` or `--output-format` | None found |
| Cursor desktop | Agent hooks | Conversation ID plus per-prompt generation ID | Configured composer model/model ID | Response, tool, stop, failure events; optional transcript path | None found |
| Cursor Agent CLI | JSON/stream JSON output | Session ID, tool call ID, optional request ID | Init event model | Terminal result when present; resume by chat/session | None found |

“None found” is a bounded research result, not an assertion that a private,
enterprise-only, or future interface cannot exist.

## Candidate evidence

The field order in each table is the complete #43 field matrix.

### ChatGPT desktop Codex mode: app UI and history

Official documentation establishes Codex as a distinct desktop view and says
its history remains separate from ChatGPT history. It documents model starting
defaults and local/cloud data handling, but does not document a Codex-mode
machine event or receipt API. Record & Replay observes user actions and window
content to create a reusable skill; OpenAI warns users not to enter secrets or
sensitive data. It is workflow capture, not invocation evidence. [OAI-D4]
[OAI-D5]

| Required field | Class | Exact scope and limit |
| --- | --- | --- |
| 1. Invocation/correlation identity | D | The UI groups work into Codex chats/history. No public machine-readable invocation or attempt identifier was found. |
| 2. Input/candidate binding | ? | The UI accepts prompts and files, but the source set gives no canonical input bytes, digest, or candidate binding exported for verification. |
| 3. Product/surface/applicable version | D | The documents identify the ChatGPT desktop Codex surface. They do not emit the app build with a particular result. |
| 4. Selected model | D | Workspace defaults and user model selection are documented; no invocation-bound machine field was found. |
| 5. Topology/effective-authority facts | ? | Local and cloud workflows are described, but no invocation statement binds the effective provider, policy, account, role, or authority chain. |
| 6. Result/failure/attempt identity | D | A user can review the UI result. No stable attempt ID or closed failure record was found. |
| 7. Producer/issuer origin and integrity | ? | The UI is not documented as a signed product statement; no issuer identity, event signature, or response-integrity semantics were found. |
| 8. Verification material/authenticated readback | ? | History and supported remote access are user-facing readback, not documented authenticated evidence readback or public verification material. |
| 9. Replay/retry/readback | D | Chats may be revisited. No immutable-attempt replay or retry relation is documented for this purpose. |
| 10. Retention/redaction/access | D | Product data controls and local/cloud distinctions are documented. They do not define evidence-handle retention or access. |
| 11. Protected-evidence handle | ? | Record & Replay can capture sensitive screen content and is explicitly unsuitable for secrets; no value-free protected handle is returned. |

Stronger claim excluded: the app UI alone does not prove exact prompt bytes,
effective model route, attempt closure, or product-authenticated execution. The
separate Compliance interface below has a different, workspace-scoped readback
boundary.

### ChatGPT desktop Codex mode and Codex CLI/TUI: Compliance `CODEX_LOG`

OpenAI documents that Codex usage from supported local clients is available in
the Compliance API. The public Admin OpenAPI, initially captured at v2.5.20 and
revalidated at v2.5.21, defines a Compliance Logs
Platform that lists and downloads immutable, time-windowed JSONL files. Codex
files use `type: CODEX_LOG`, a stable `event_id`, timestamp, workspace principal,
actor, normalized `client_id`, and event-specific details. Normalized client IDs
include `CODEX_CLI`, `CODEX_DESKTOP_APP`, and `CODEX_CHATGPT_DESKTOP` as distinct
enum values. The `CODEX_LOG.client_id` prose calls the value a normalized Codex
client identifier and gives `CODEX_DESKTOP_APP` as an example, but does not
formally type that field as `CodexClient` or specify which desktop identifier the
unified ChatGPT Codex mode emits. `PROMPT_SENT` and
`PROMPT_RESPONSE_RECEIVED` details include session ID, optional turn/call IDs,
prompt or response text, model, environment ID, status, service tier, reasoning
effort, and token usage as applicable. [OAI-D4] [OAI-D6]

The platform authenticates an Admin API reader by fine-grained scope, returns a
short-lived signed HTTPS download URL, and says files are immutable once
written. Required `ComplianceLogFileMetadata.file_sha256` binds the authenticated
list metadata to a SHA-256 digest of the complete downloaded file and lets the
reader check file-content integrity. That is product-authenticated readback plus
content-integrity material at retrieval time. It is not an event/file digital
signature: the schema exports no signature, issuer key, or public verification
material. Files expire after 30 days;
delivery is at least once, duplicates can cross files, late events can arrive,
and a stable `event_id` is the documented deduplication key. Freshness does not
guarantee completeness. [OAI-D6]

| Required field | Class | Exact scope and limit |
| --- | --- | --- |
| 1. Invocation/correlation identity | A | Authenticated `CODEX_LOG` readback carries stable event ID, session ID, and optional turn/call IDs. Prompt and response remain separate events; optional IDs may be absent. |
| 2. Input/candidate binding | A | `PROMPT_SENT` records extracted prompt text with correlation fields; text may be empty for non-text input. There is no canonical full-input or candidate digest. |
| 3. Product/surface/applicable version | A | Each event authenticates its recorded normalized client identifier and workspace. `CodexClient` contains `CODEX_CLI`, `CODEX_DESKTOP_APP`, and `CODEX_CHATGPT_DESKTOP`, but the log prose is not formally typed to that enum; no app/CLI build is included, and the emitted mapping and exhaustive desktop coverage remain unknown. |
| 4. Selected model | A | Prompt model is optional; response model is documented. The log authenticates the recorded product value, not an independently verifiable upstream model-service statement. |
| 5. Topology/effective-authority facts | A | Principal, actor, workspace, client, optional environment, model, service tier, and reasoning effort are available. Policy ancestry, account route, provider endpoint, and capability authority remain incomplete. |
| 6. Result/failure/attempt identity | A | Response status, event/session/optional turn/call IDs, and tool success/failure events give product-readback outcomes. The schema does not combine them into one atomic closed attempt receipt. |
| 7. Producer/issuer origin and integrity | A | Exact semantics are scoped Admin API authorization, HTTPS retrieval, a short-lived signed download URL, an OpenAI assertion that completed files are immutable, and authenticated metadata containing the required whole-file `file_sha256`. The digest checks content equality; no event/file signature or offline issuer proof is exported. |
| 8. Verification material/authenticated readback | A | This is authenticated product readback through a workspace-scoped API key. Authenticated list metadata exports whole-file integrity material in `file_sha256`; it exports no public origin-verification key or signature, and detached third parties cannot authenticate OpenAI from the digest alone. |
| 9. Replay/retry/readback | D | File delivery is at least once with stable-event-ID deduplication and possible late arrival. These are log-delivery semantics, not inference retry or immutable linked-attempt semantics. |
| 10. Retention/redaction/access | D | Files expire after 30 days and access is scope-gated. Prompt/response/tool fields can contain raw protected evidence; no field-level redaction contract is stated for these events. |
| 11. Protected-evidence handle | D | Event ID is stable for deduplication, and file ID plus `file_sha256` locates a retained file and checks its downloaded contents. They do not provide single-event lookup, post-expiry stability, protected-store semantics, portable OpenAI authentication, candidate binding, authority binding, or a closed value-free protected-reference contract. |

This candidate is the strongest product-owned evidence surface in the survey,
but it is conditional on covered workspace use and authorized export. The
public sources do not establish whether a direct API-key Responses API
invocation is included; the CLI client name alone cannot establish that
coverage. They also do not state which of `CODEX_DESKTOP_APP` and
`CODEX_CHATGPT_DESKTOP` unified ChatGPT desktop Codex mode emits, under what
conditions, or whether its event coverage is exhaustive. Retained authenticated
metadata and checksum-verified bytes can support a controller observation, but
the digest alone does not turn the JSONL file into a publicly verifiable OpenAI
receipt after the authenticated retrieval context is lost.

The separate Codex Enterprise Analytics endpoints return daily aggregate usage
and review metrics. They are useful for adoption reporting but do not bind one
invocation, so they are screened out rather than treated as an invocation
candidate.

### Codex CLI/TUI: `codex exec --json`

The non-interactive documentation describes JSONL events and resume by session
ID. The pinned `exec_events.rs` schema is byte-identical in public release tags
`rust-v0.152.1` and `rust-v0.153.4`: it emits a thread ID, empty turn-start
payload, usage or error at turn end, and item IDs plus typed payloads. It emits
no turn ID, product version, model, signature, or verification key. [OAI-D1]
[OAI-S1]

| Required field | Class | Exact scope and limit |
| --- | --- | --- |
| 1. Invocation/correlation identity | C | `thread.started.thread_id` and item IDs correlate one local stream; the turn-start event has no turn ID. |
| 2. Input/candidate binding | C | A controller can bind the command input it supplied to the stdout stream it captured. The product stream does not re-emit canonical input bytes or a digest. |
| 3. Product/surface/applicable version | P | Identical schema bytes were verified at Codex 0.152.1 and 0.153.4 tags. The event stream itself does not state its CLI version. |
| 4. Selected model | C | A controller can observe the model option/configuration it invoked. The JSONL event schema does not repeat or authenticate it. |
| 5. Topology/effective-authority facts | ? | The event schema supplies no effective provider, account, policy ancestry, or capability authority. |
| 6. Result/failure/attempt identity | C | `turn.completed`, `turn.failed`, fatal `error`, and item terminal states report outcomes. There is no distinct turn/attempt ID in this schema. |
| 7. Producer/issuer origin and integrity | ? | No issuer, signature, MAC, signed response identity, or event-chain integrity is specified. |
| 8. Verification material/authenticated readback | D | Resume by thread/session ID is documented. It is continuation/readback, not authenticated receipt readback, and no public verification material is exported. |
| 9. Replay/retry/readback | D | Resume is documented; retry linkage, idempotency, and immutable attempt relations are not. |
| 10. Retention/redaction/access | ? | The JSONL interface documents output, not a retention, redaction, or evidence-access contract. Raw prompts, messages, commands, and tool output may be sensitive. |
| 11. Protected-evidence handle | ? | No value-free reference replaces raw event content. A controller-authored reference would be external to the interface. |

Stronger claim excluded: a thread ID plus terminal event can support local
correlation, but it does not bind the exact candidate or model and is not a
product-issued receipt.

### Codex CLI/TUI: app-server v2 and current attachment extension

Public 0.152.1 and 0.153.4 source defines app-server v2 thread/turn protocols.
The 0.153.4 thread record includes thread and session IDs, model provider,
configured model, timestamps, state, source, working directory, CLI version,
and turns; the configured model is explicitly not per-turn execution telemetry.
Turn-start accepts thread ID, optional client message ID, input, working
directory, model/configuration overrides, and experimental client metadata.
Turns have IDs, items, status, error, and timing. `thread/read` reads persisted
local history. [OAI-S2]

The source revision current at initial observation adds stored thread
attachments, but both historical tags lack `thread_attachment.rs`. Fresh Codex
main revision `f3da3861c557b4813d9840177a45940a465f9efe` retained byte-identical
`thread_attachment.rs` content and materially unchanged attachment behavior in
the app-server README. The attachment facts below therefore apply to initial
revision `50d77959bf927293c4b5ddcca81d05331ae582ea` and that fresh revision, not to
the historically observed 0.152.1 or 0.153.4 builds. [OAI-S3]

| Required field | Class | Exact scope and limit |
| --- | --- | --- |
| 1. Invocation/correlation identity | P | Thread, session, optional client-message, turn, and item IDs define a rich local correlation graph. |
| 2. Input/candidate binding | P | Turn-start carries structured user input and optional caller metadata. No canonical candidate digest or immutable binding is generated by the product. |
| 3. Product/surface/applicable version | P | Thread records include CLI version and source. Historical source is pinned separately to 0.152.1/0.153.4; attachment behavior is current-source-only. |
| 4. Selected model | P | Thread/turn configuration carries a model, but source explicitly says the thread model is not per-turn execution telemetry. |
| 5. Topology/effective-authority facts | P | Source, model provider, working directory, policies, and configuration are exposed. They do not establish the complete effective provider/account/authority chain. |
| 6. Result/failure/attempt identity | P | Turn ID, status, error, items, and timing provide closed local lifecycle records when retained. |
| 7. Producer/issuer origin and integrity | ? | Local protocol origin is not a documented cryptographic issuer. No per-result signature, MAC, or signed event chain was found. |
| 8. Verification material/authenticated readback | P | `thread/read` returns persisted local history. It is not documented as authenticated product readback, and no public verification material is exported. |
| 9. Replay/retry/readback | P | Read, resume, and fork exist. Forked attachment copying is best-effort in current source; no exactly-once attempt ledger is defined. |
| 10. Retention/redaction/access | P | Ephemeral/history state and local paths are represented. Current attachments are deleted with the owning thread. No protected-store access or redaction policy follows. |
| 11. Protected-evidence handle | P | Current attachments offer stable thread-local IDs and idempotent type/key lookup with arbitrary payload. They do not provide confidentiality, evidence authenticity, global stability, or historical-version applicability. |

Stronger claim excluded: app-server has the richest Codex structure in this
survey, but configured state and persisted history are not evidence that the
backend used that state, and current attachments are a carrier—not a protected
evidence contract.

### Codex CLI/TUI: lifecycle hooks

Current Codex hook documentation describes local lifecycle callbacks with
common session ID, transcript path, working directory, event name, active model
slug, and turn-scoped turn ID. Prompt, tool, and stop events can expose raw
content and outcomes. The documentation also says the transcript format is not
stable. [OAI-D3]

| Required field | Class | Exact scope and limit |
| --- | --- | --- |
| 1. Invocation/correlation identity | C | Session and turn IDs correlate callbacks for a local controller. |
| 2. Input/candidate binding | C | Prompt hooks expose raw submitted prompt data; no canonical digest or frozen-candidate identifier is created. |
| 3. Product/surface/applicable version | ? | The dated document applies to current Codex, but the hook payload does not establish product build and applicability to the historical versions was not pinned. |
| 4. Selected model | C | The common hook input reports the active model slug. It is a local callback field, not verified backend execution telemetry. |
| 5. Topology/effective-authority facts | ? | Working directory and lifecycle context are insufficient to establish route or effective authority. |
| 6. Result/failure/attempt identity | C | Turn/tool/stop callbacks expose local lifecycle outcomes. Completeness across abrupt termination is not established. |
| 7. Producer/issuer origin and integrity | ? | A spawned local hook receives product-written JSON, but no per-event signature or independent issuer verification is documented. |
| 8. Verification material/authenticated readback | C | `transcript_path` permits local readback, while the transcript format is expressly unstable; it is not authenticated evidence readback. |
| 9. Replay/retry/readback | ? | No immutable retry relation or replay contract was found. |
| 10. Retention/redaction/access | ? | Local transcript location is exposed, but retention and access depend on local product/controller state. Raw hook data may be sensitive. |
| 11. Protected-evidence handle | ? | The hook supplies raw values and paths, not a value-free authenticated reference. |

Stronger claim excluded: deterministic callback timing does not make a hook
payload an independently verifiable product statement.

### Claude Code: headless JSON and stream JSON

The headless interface documents `--output-format json` and `stream-json`.
Structured output includes result, session ID, and metadata; stream mode emits
message and lifecycle events, including `system/api_retry` before a retryable
API retry. Session documentation describes local persistence, resume, and
forking. [ANT-D1] [ANT-D3]

| Required field | Class | Exact scope and limit |
| --- | --- | --- |
| 1. Invocation/correlation identity | C | Session ID and streamed message/tool identities correlate one local run. |
| 2. Input/candidate binding | C | The controller supplies the prompt and may observe user-message events. No product-created digest binds canonical candidate bytes. |
| 3. Product/surface/applicable version | ? | The output is documented for current Claude Code, but a terminal invocation record does not establish the CLI build. |
| 4. Selected model | C | Stream/message metadata and model-usage information identify model values observed by the controller; they are not independently authenticated. |
| 5. Topology/effective-authority facts | ? | The reviewed CLI output does not close the effective provider, gateway, account, policy, or authority chain. |
| 6. Result/failure/attempt identity | C | Result/error metadata, stop reason, messages, tool IDs, and API retry events expose local outcomes and partial attempt structure. |
| 7. Producer/issuer origin and integrity | ? | No signed result, issuer chain, event MAC, or durable response-integrity semantics were found. |
| 8. Verification material/authenticated readback | D | Persisted local sessions may be resumed/read. No public verification key or authenticated service readback for the invocation is documented. |
| 9. Replay/retry/readback | C | API retry events expose retry attempts; resume and fork are documented. They do not define a Q10 immutable linked-attempt ledger. |
| 10. Retention/redaction/access | D | Sessions are persisted locally by default; SDK variants can alter persistence. This is a local storage behavior, not a protected evidence policy. |
| 11. Protected-evidence handle | ? | Session IDs locate local session state but have no documented protected-store, value-free, or authenticated-readback semantics. |

Stronger claim excluded: a `session_id` or retry event does not prove a unique
backend attempt or authenticate the result.

### Claude Code: Agent SDK message stream

Pinned Python Agent SDK v0.2.153 source defines assistant messages with model,
message ID, stop reason, session ID, and UUID; result messages with timing,
error state, turn count, session ID, result, structured output, model usage,
permission denials, API error status, UUID, terminal reason, and semantic
origin; and stream events with UUID, session ID, and raw API event. [ANT-S1]

| Required field | Class | Exact scope and limit |
| --- | --- | --- |
| 1. Invocation/correlation identity | P | Session ID, message ID/UUID, stream UUID, and tool IDs define typed correlation fields. |
| 2. Input/candidate binding | C | The SDK caller controls input and can record matching user-message bytes. No native candidate digest is defined. |
| 3. Product/surface/applicable version | P | The schema is pinned to Agent SDK Python v0.2.153. It does not prove the bundled or external Claude Code runtime version for an invocation. |
| 4. Selected model | P | Assistant messages carry `model`; result `model_usage` can contain canonical model metadata. These are unsigned message fields. |
| 5. Topology/effective-authority facts | P | Current model-usage types can report a provider label. That semantic label does not establish account, gateway, policy ancestry, or capability authority. |
| 6. Result/failure/attempt identity | P | Typed result fields cover error, stop/terminal reason, turns, usage, denials, and API status. Completeness still depends on receiving the terminal message. |
| 7. Producer/issuer origin and integrity | P | `origin` is semantic message provenance, not cryptographic issuer authentication. No signature/MAC field is defined. |
| 8. Verification material/authenticated readback | D | SDK session APIs can use persisted sessions/stores; no product verification material or authenticated invocation readback is documented. |
| 9. Replay/retry/readback | D | Resume/fork/session-store behavior is documented. No exactly-once or immutable linked-attempt contract follows. |
| 10. Retention/redaction/access | D | Local persistence and optional external session mirroring are controller storage choices; mirror failure can leave a missing external batch. |
| 11. Protected-evidence handle | ? | Session keys/IDs are locators, not documented value-free protected-evidence handles with authentication and access semantics. |

Stronger claim excluded: a typed SDK object makes integration safer, but type
shape and semantic `origin` do not authenticate the producing service.

### Claude Code: hooks

Claude Code hooks receive JSON through a command's stdin or an HTTP POST. Common
fields include session ID, transcript path, working directory, permission mode,
and event name; individual hooks expose prompts, tools, results, sources, and
model values. HTTP hooks may use caller-supplied authorization headers. That
authenticates the controller's endpoint access when configured; it is not a
product signature over the invocation. [ANT-D2]

| Required field | Class | Exact scope and limit |
| --- | --- | --- |
| 1. Invocation/correlation identity | C | Session ID and event/tool identifiers correlate hook callbacks. |
| 2. Input/candidate binding | C | `UserPromptSubmit` and tool hooks expose raw input. No native canonical digest or frozen-candidate binding is created. |
| 3. Product/surface/applicable version | ? | The hook payload does not bind the Claude Code version; individual newer fields have documented minimum versions, so consumers must version-gate them. |
| 4. Selected model | C | Session-start and related events can report model data. It remains a local event field. |
| 5. Topology/effective-authority facts | ? | Source, permission mode, and environment context do not close the provider/account/authority topology. |
| 6. Result/failure/attempt identity | C | Stop, subagent, tool, and failure-related callbacks expose lifecycle state, but a universal terminal receipt is not defined. |
| 7. Producer/issuer origin and integrity | D | Command/HTTP delivery and optional controller header semantics are documented. No product-issued per-event signature is. |
| 8. Verification material/authenticated readback | C | Transcript path enables local readback; it does not authenticate a service result or export verification material. |
| 9. Replay/retry/readback | ? | Hook re-execution and duplicate-delivery semantics sufficient for immutable attempts were not established. |
| 10. Retention/redaction/access | ? | Retention follows local transcripts and the hook receiver. Raw prompts/tool values require controller-side protection. |
| 11. Protected-evidence handle | ? | A hook receiver could author an opaque external reference, but Claude Code does not define or verify that reference. |

Stronger claim excluded: an authenticated HTTP hook endpoint can know which
client credential reached it; it still lacks a product-signed statement of
what the model service executed.

### Claude Desktop: Code-tab UI and shared hooks

The official Desktop page scopes this candidate to the **Code tab**, not the
separate Claude Desktop chat MCP configuration. It says Code-tab sessions share
Claude Code hooks and settings, expose selectable models and transcript views,
and can reopen sessions from the sidebar. It expressly says `--print` and
`--output-format` are unavailable because Desktop is interactive only. [ANT-D4]

| Required field | Class | Exact scope and limit |
| --- | --- | --- |
| 1. Invocation/correlation identity | C | Shared Claude Code hooks provide a session ID for Code-tab sessions; the GUI also groups work by session. |
| 2. Input/candidate binding | C | Shared prompt hooks can observe raw input. The GUI does not export canonical candidate bytes or a digest. |
| 3. Product/surface/applicable version | D | The page establishes Code-tab applicability, but neither shared hook payload nor transcript binds the Desktop app version to a result. |
| 4. Selected model | C | Desktop exposes a model picker and shared hooks can report model context. Neither proves the effective backend route. |
| 5. Topology/effective-authority facts | D | The page documents default and enterprise provider options. It does not emit invocation-bound effective authority. |
| 6. Result/failure/attempt identity | C | UI transcript plus shared stop/tool hooks expose local outcomes; Desktop has no standalone machine-output result interface. |
| 7. Producer/issuer origin and integrity | ? | No Desktop-issued signature, MAC, or independently verifiable origin statement was found. |
| 8. Verification material/authenticated readback | D | Sidebar/transcript readback is interactive. `--print` and `--output-format` are expressly unavailable; no authenticated evidence readback is documented. |
| 9. Replay/retry/readback | D | Existing sessions can be reopened. No immutable replay/retry relation is defined. |
| 10. Retention/redaction/access | ? | View modes affect display, not evidence retention or redaction. Shared local session state is not a protected-store contract. |
| 11. Protected-evidence handle | ? | No value-free handle interface is documented. |

Stronger claim excluded: Code-tab hook reuse makes some Claude Code controller
observations available, but it does not turn the interactive Desktop transcript
into a product-authenticated receipt. General Claude Desktop chat remains
outside the documented Code-tab hook boundary and is unknown here.

### Cursor desktop: Agent hooks

Cursor hooks are local child processes receiving JSON on stdin. Common input
contains conversation ID stable across turns, generation ID changing with each
user message, configured model/model ID and parameters, Cursor version,
workspace roots, optional authenticated-user email, and nullable transcript
path. Prompt, response, tool, stop, failure, session-start, and session-end hooks
add lifecycle-specific data. The model field is documented as the configured
composer model, not as backend execution attestation. [CUR-D1]

| Required field | Class | Exact scope and limit |
| --- | --- | --- |
| 1. Invocation/correlation identity | C | Conversation ID plus per-prompt generation ID and tool-use IDs give the strongest direct turn correlation in the surveyed desktop hooks. |
| 2. Input/candidate binding | C | `beforeSubmitPrompt` exposes raw prompt and attachments. No canonical candidate digest or immutable bind is generated. |
| 3. Product/surface/applicable version | C | Hook input reports `cursor_version` and applies to Agent Chat/Cmd+K. A field's presence still needs version-aware parsing. |
| 4. Selected model | C | `model`, optional structured `model_id`, and parameters describe configured selection, not authenticated effective execution. |
| 5. Topology/effective-authority facts | ? | Workspace and user context do not establish provider, account policy, gateway, or capability authority. |
| 6. Result/failure/attempt identity | C | Response, tool, stop, failure, and session-end events expose local lifecycle state. Hook failure behavior means observation completeness must not be assumed. |
| 7. Producer/issuer origin and integrity | D | Cursor spawns the hook process and writes JSON locally. No per-event product signature/MAC or verifier key is documented. |
| 8. Verification material/authenticated readback | C | `transcript_path` can point to local history and is null when transcripts are disabled. It is not authenticated product readback. |
| 9. Replay/retry/readback | ? | No immutable replay, retry-link, or exactly-once delivery contract was found. |
| 10. Retention/redaction/access | D | Transcripts can be disabled; hooks receive potentially sensitive raw fields. No evidence-specific retention, redaction, or protected access scope is defined. |
| 11. Protected-evidence handle | ? | No native value-free protected reference is returned or verified. |

Stronger claim excluded: `model_id`, `cursor_version`, and `generation_id` make
a good controller correlation tuple, but they are unsigned local fields and do
not attest to the effective model service or authority.

### Cursor Agent CLI: JSON and stream JSON

Cursor documents `--output-format json` and `stream-json`. Stream init includes
session ID, model, working directory, permission mode, and API-key source; user
and tool events include raw content and call IDs; a success result includes
duration, final text, session ID, and optional request ID. The documentation
warns that errors can exit nonzero and a stream can end without a terminal
result. Resume accepts a chat/session selector. [CUR-D2] [CUR-D3]

| Required field | Class | Exact scope and limit |
| --- | --- | --- |
| 1. Invocation/correlation identity | C | Session ID, tool call IDs, and optional terminal request ID correlate local events. Request ID semantics are not documented as receipt identity. |
| 2. Input/candidate binding | C | The stream can include the raw user message supplied by the controller. No product-created candidate digest exists. |
| 3. Product/surface/applicable version | ? | The current output format is documented, but init/result does not bind the Agent CLI version. |
| 4. Selected model | C | Init reports the selected model. It is not an authenticated statement of effective backend execution. |
| 5. Topology/effective-authority facts | C | Working directory, permission mode, and API-key source are controller-visible context; they do not close effective provider/account authority. |
| 6. Result/failure/attempt identity | C | Success result and tool completion events are structured. A failure may terminate without a terminal result, so absence remains indeterminate. |
| 7. Producer/issuer origin and integrity | ? | No per-result signature, MAC, issuer chain, or independently checkable response integrity was found. |
| 8. Verification material/authenticated readback | D | Resume/readback by chat/session is documented; it is not authenticated receipt readback, and no verification material is exported. |
| 9. Replay/retry/readback | D | Resume is supported. Retry identity, idempotency, and immutable attempt linkage are not documented. |
| 10. Retention/redaction/access | ? | The output contains raw prompts/results/tool data; no evidence-specific retention, redaction, or access contract was found. |
| 11. Protected-evidence handle | ? | Session/request IDs do not carry documented protected-store lookup, value-free, or authenticity semantics. |

Stronger claim excluded: the optional request ID and selected-model init field
do not create an authenticated service receipt, and a missing terminal event
must remain indeterminate rather than be recorded as a clean failure.

## Authentication and readback boundary

The survey found four different mechanisms that must stay separate:

1. **Client or hook transport authentication.** Sign-in, API credentials, or a
   controller-supplied HTTP-hook bearer token may authenticate access. They do
   not yield a portable signed statement over the invocation.
2. **Native/controller-visible evidence.** JSONL, JSON-RPC, SDK objects, hooks,
   request IDs, session IDs, and local transcripts support correlation and
   debugging. Their values can be placed in a controller-authored observation,
   subject to that controller's trust boundary.
3. **Scoped product-authenticated readback.** OpenAI Compliance `CODEX_LOG`
   authenticates an authorized reader and supplies immutable product log files
   through a short-lived signed download URL. Required authenticated metadata
   includes `file_sha256`, which verifies equality of the downloaded whole-file
   bytes. This establishes retrieval-time product origin and file-content
   integrity within the Admin API boundary, not a portable event signature.
4. **Portable product-authenticated evidence.** Q11 needs an asymmetric
   statement bound to a capability-scoped authority generation and exact
   invocation facts. No surveyed interface exports such a statement or the
   public verification material needed to validate it independently.

Package signatures, release checksums, and pinned source establish distribution
or source identity at their respective layers. They do not authenticate an
invocation. Likewise, a TLS-protected response or native local process channel
does not remain independently verifiable after capture unless an owning source
defines a durable authenticated statement; none reviewed here does.

The full Admin response-schema check also found
`RemoteControlClient.device_key_public_spki_der_base64` with device key ID,
algorithm, and protection-class metadata. No reviewed source binds that device
key to a `CODEX_LOG` event or file signature, the downloaded bytes, a candidate,
or a Q11 capability-scoped authority generation. It is therefore public-key
metadata for a different Admin resource, not invocation-verification material
for a candidate in this survey.

Readback narrows uncertainty only at the layer it proves. Compliance readback
authenticates OpenAI's retained Codex log metadata and fields within its
workspace, scope, retention, and transport boundary, and `file_sha256` checks
the downloaded file contents against that metadata. Neither the digest nor the
readback authenticates exact candidate bytes, the complete effective inference
authority, or a capability-scoped issuer generation. Codex `thread/read`,
Claude session resume/read, Cursor transcript paths, and UI history show only
retained local product state and are not authenticated producer readback.

## Protected-evidence transport boundary

A handle suitable for #8 would need all of the following to be settled by its
responsible producer/store, not inferred from a string ID:

- value-free syntax in the portable receipt;
- unambiguous binding to exact protected bytes and their evidence class;
- stable namespace, lookup, and version semantics;
- authenticated readback and verifier authorization;
- retention, deletion, redaction, and access rules; and
- explicit behavior for retries, forks, copies, missing data, and revocation.

No selected surface supplies that closed contract.

Compliance file ID plus `file_sha256` is the closest native file-level locator
and integrity pair, but it still fails the handle contract. It expires with the
retained file, has no single-event lookup or protected-store semantics, and does
not carry portable OpenAI origin, candidate, authority-generation, or
qualification authentication.

Current Codex thread attachments are useful evidence for a possible carrier
shape because they separate a stable resource identity from conversation
history and support idempotent lookup. Their payload is arbitrary JSON, their
identity is thread-local, fork copying is best-effort, the referenced resource
is not copied, and owning-thread deletion removes the attachment. Nothing in
the interface protects the payload, makes it value-free, authenticates an
external resource, or binds it to an invocation result. The API is therefore a
transport primitive only and must not be named a receipt or protected-evidence
handle without a separately owned contract. [OAI-S3]

Every hook/controller candidate could replace captured raw evidence with an
opaque external reference before constructing a portable record. That is an
implementation possibility, not a native capability finding. Its authenticity,
retention, access, and failure semantics would belong to the still-unselected
producer/store and must be decided by #8 rather than standardized by this
report.

## Inputs for the #8 decision owner

The public evidence supports these bounded decision inputs without reopening
Q1–Q11:

- Treat native local event interfaces as adapters for controller observations,
  not as candidate production issuers on the evidence reviewed here. Treat
  Compliance `CODEX_LOG` as scoped product readback with finite retention and a
  required whole-file integrity digest, not as a portable Q11 signature. A
  controller may retain and sign the authenticated metadata and verified file
  digest as its own observation without promoting it to OpenAI-issued proof.
- Preserve an explicit assurance class on every collected fact. A configured
  model, provider label, UI selection, or controller command is not effective
  execution authority.
- Preserve indeterminate outcomes. In particular, Cursor Agent CLI can end
  without a terminal event, and callback/session readback completeness is not
  universally guaranteed.
- If native correlation is consumed, use the strongest surface-specific tuple
  available and include the exact product/interface version separately. Do not
  normalize away missing attempt IDs.
- Keep protected raw events out of the portable record. A later producer may
  emit a value-free reference, but the reference contract and authenticated
  readback must be independently specified and reviewed.
- Require the selected producer/issuer design to add the missing Q11
  authenticity and verification boundary; none of the surveyed native surfaces
  closes it.

Unresolved for #8—not for this research increment—are the real provider
descriptor, producer placement, issuer/custody choice, public-key distribution,
protected-store design, and the exact mapping from controller observations to
the accepted closed receipt payloads. Two public-interface coverage questions
also remain unresolved: whether direct API-key Codex CLI use enters
`CODEX_LOG`, which of `CODEX_DESKTOP_APP` and `CODEX_CHATGPT_DESKTOP` the unified
ChatGPT desktop Codex mode emits under each condition, and whether its event
coverage is exhaustive. The parallel #44 signing/custody study is
independent and was not consumed as an answer here.

## Evidence limits and validation

This is static public-source evidence. It does not establish live availability,
runtime behavior, a current host version, account entitlement, backend routing,
or qualification of any candidate. Moving documentation may change after the
observation date. Pinned source fixes only the cited source shape; it does not
prove that a vendor-distributed binary contains or executed it.

The historical inventory recorded ChatGPT desktop 26.901.51231; Codex CLI
0.152.1 and 0.153.4; Claude Code 2.1.239 and 2.1.263; Claude Desktop 1.40609 and
1.46388.4; Cursor desktop 3.15.19 and 3.18.25; and Cursor Agent 2026.08.11 and
2026.09.02 on 2026-09-07. Those are retained solely as applicability questions.
Only the Codex `exec_events.rs` byte identity was checked directly against both
historical public tags. No other current document or source claim is promoted
to either historical build without an explicit version statement.

The latest candidate was checked against five security-evidence criteria:

1. every selected surface and every evidenced candidate has all eleven fields;
2. unknown and expressly unsupported remain distinct;
3. local logs, semantic origin fields, request IDs, checksums, and pinned source
   are not promoted to product authentication, while Compliance readback and its
   required file checksum are not promoted beyond documented scoped
   HTTPS/metadata/content-integrity boundaries;
4. retry, readback, retention, and protected-handle limits are explicit; and
5. source claims are immutable while moving documentation is dated and
   content-digested where retrievable.

The checksum miss establishes a reusable research correction that the inspected
public equipment does not completely own. The issue contract requires field and
evidence-class coverage, and the composition contract forbids evidence-class
promotion; the installed `research` procedure requires primary sources, while
security validation requires evidence and proof gaps. None explicitly requires
recursive response-schema traversal before a categorical absence claim. A
separate capture proposal should extend the maintained `research` procedure:
before saying an API exports no digest or verification material, resolve list
and read response references, inspect response-metadata schemas, and search for
checksum, digest, signature, MAC, key, and ETag fields; then classify content
integrity, origin, candidate identity, authority, and qualification separately.
The operator must decide the maintained source/placement because this increment
cannot inspect or edit shared ownership sources. #43's next review and #44's
research are direct consumers. The authorized two-document method and manifest
traceability have been corrected here without installing a global convention.

## Primary sources

The JSON source manifest is authoritative for retrieval timestamps and content
digests.

- **[OAI-D1]** OpenAI, [Non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode), moving documentation observed 2026-09-16.
- **[OAI-D2]** OpenAI, [App server](https://learn.chatgpt.com/docs/app-server), moving documentation observed 2026-09-16.
- **[OAI-D3]** OpenAI, [Hooks](https://learn.chatgpt.com/docs/hooks), moving documentation observed 2026-09-16.
- **[OAI-D4]** OpenAI, [Using Codex with your ChatGPT plan](https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan), moving documentation observed 2026-09-16.
- **[OAI-D5]** OpenAI, [ChatGPT Work and Codex](https://help.openai.com/en/articles/20001275), moving documentation observed 2026-09-16.
- **[OAI-D6]** OpenAI, [Programmatic Admin Platform API reference](https://chatgpt.com/public/admin/api-reference) and [OpenAPI download](https://chatgpt.com/public/admin/api-reference/openapi.json), moving public schema initially captured at v2.5.20 and freshly revalidated at v2.5.21 on 2026-09-17T03:46:16Z.
- **[OAI-S1]** OpenAI Codex 0.153.4, [`exec_events.rs`](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/exec/src/exec_events.rs#L8-L132); the file has the same Git blob and SHA-256 at 0.152.1 commit `5adb68a49933ae446bf11935662c83dba55a0804`.
- **[OAI-S2]** OpenAI Codex app-server v2 at [0.152.1](https://github.com/openai/codex/blob/5adb68a49933ae446bf11935662c83dba55a0804/codex-rs/app-server-protocol/src/protocol/v2/turn.rs#L152-L191) and 0.153.4 [`turn.rs`](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/app-server-protocol/src/protocol/v2/turn.rs#L156-L210), [`thread_data.rs`](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/app-server-protocol/src/protocol/v2/thread_data.rs#L203-L399), and [`thread.rs`](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/app-server-protocol/src/protocol/v2/thread.rs#L1656-L1674).
- **[OAI-S3]** OpenAI Codex source initially observed at `50d77959bf927293c4b5ddcca81d05331ae582ea`, [`thread_attachment.rs`](https://github.com/openai/codex/blob/50d77959bf927293c4b5ddcca81d05331ae582ea/codex-rs/app-server-protocol/src/protocol/v2/thread_attachment.rs#L9-L106) and [app-server attachment behavior](https://github.com/openai/codex/blob/50d77959bf927293c4b5ddcca81d05331ae582ea/codex-rs/app-server/README.md#L155-L218); freshly revalidated at current revision [`f3da3861c557b4813d9840177a45940a465f9efe`](https://github.com/openai/codex/tree/f3da3861c557b4813d9840177a45940a465f9efe).
- **[ANT-D1]** Anthropic, [Run Claude Code programmatically](https://code.claude.com/docs/en/headless), moving documentation observed 2026-09-16.
- **[ANT-D2]** Anthropic, [Hooks reference](https://code.claude.com/docs/en/hooks), moving documentation observed 2026-09-16.
- **[ANT-D3]** Anthropic, [Manage sessions](https://code.claude.com/docs/en/sessions), moving documentation observed 2026-09-16.
- **[ANT-D4]** Anthropic, [Use Claude Code Desktop](https://code.claude.com/docs/en/desktop), moving documentation observed 2026-09-16.
- **[ANT-S1]** Anthropic Claude Agent SDK Python v0.2.153, [`types.py`](https://github.com/anthropics/claude-agent-sdk-python/blob/763922b0de2c9fb5371504d73ae54cde49536fe1/src/claude_agent_sdk/types.py#L1139-L1387).
- **[CUR-D1]** Cursor, [Hooks](https://cursor.com/docs/hooks), moving documentation observed 2026-09-16.
- **[CUR-D2]** Cursor, [Agent CLI output format](https://cursor.com/docs/cli/reference/output-format), moving documentation observed 2026-09-16.
- **[CUR-D3]** Cursor, [Agent CLI parameters](https://cursor.com/docs/cli/reference/parameters), moving documentation observed 2026-09-16.
