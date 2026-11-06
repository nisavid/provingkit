# Daybreak invocation surfaces

An ordinary-model Advisor created a fresh chat through the existing desktop
manager, then ran an explicitly selected `gpt-6-sol` / medium / Daybreak Blue
turn in that chat. The November 6 test used a harmless first-turn sentinel,
followed by the explicit Blue turn; both completed, and the second turn's
persisted context recorded `cyber_access_program = daybreak_blue`. The new chat
had no fork origin. The Advisor stayed on `gpt-6-astra` with Daybreak unset.

This verifies a two-turn fresh-worker bootstrap. Daybreak on the first turn
from an ordinary Advisor remains unqualified. The exact creation and subsequent
turn sequence is recorded below under [Fresh worker bootstrap](#fresh-worker-bootstrap).

The original November 5 isolated-turn experiment used this sequence:

1. Fork the existing harmless legacy probe using native `fork_thread` with
   `environment: {type: "same-directory"}`. Use the returned child ID; this fork
   carries the seed's history.
2. Connect to the existing desktop IPC listener, initialize, discover the child's
   owner, and target that owner for subsequent calls.
3. Set the child's saved choice with `thread-follower-update-daybreak` and read
   it back as `true`.
4. Submit one `thread-follower-start-turn` request with `model: "gpt-6-sol"`,
   `effort: "medium"`, and `cyberAccessProgram: "daybreakBlue"`, binding the same
   model and effort in `collaborationMode.settings`.
5. Match the response and obtain `result.result.turn.id`. Check native terminal
   output and that turn's persisted context, then recheck the Advisor and seed.

The fork preserved the seed for this experiment. It is not a Daybreak
prerequisite: the follower update/start handlers require the targeted
conversation's owner, with no fork-ancestry condition. The same operations can
target an existing owned thread, including the seed, subject to ordinary access
and turn-state checks. That would change the seed and add a turn to its history;
this experiment did not do so. [Follower handlers][ipc-manager]

That original experiment verified the internal-IPC turn route. The later
bootstrap adds fresh native creation; neither observation establishes direct
explicit Daybreak selection through `create_thread` or independent provider-side
attestation. The native creation wrapper rejected the explicit Daybreak fields.

This research records source, schema, and bounded runtime observations made on
November 5–6, 2026. It supports the
[Daybreak invocation migration map](https://github.com/nisavid/provingkit/issues/871)
and its
[initial dispatch decision](https://github.com/nisavid/provingkit/issues/872).
Product migration, qualification, publication, installation, and release
acceptance remain separate.

## Scope and evidence

The verified increment is ordinary-model Advisor execution of an isolated
Daybreak child through the existing desktop App Server manager, with the Advisor
and original seed preserved. CLI and cross-harness consumers remain separate
questions; support on this desktop route does not establish support elsewhere.

The research used the installed first-party desktop distribution and its schema
generator. Source inspection and schema generation did not create a model turn,
change an account, or start a server. Dispatch executed one authorized
legacy-route probe. Exact-ID read-only database lookups and allowlisted
turn-context fields supplied the metadata evidence below. The explicit native
wrapper attempt returned an argument error before creating a thread. The
existing-app IPC connection subsequently completed the explicit child-turn
probe. Schema generation emitted a warning that it could not create PATH aliases
on the read-only filesystem, then completed successfully. The interfaces below
identify the binary and artifacts needed to regenerate those schemas.

| Artifact | Observed identity |
| --- | --- |
| Desktop package | ChatGPT desktop `26.1029.61003`, production Linux package |
| Desktop bundled CLI | `codex-cli 0.166.0-alpha.6` |
| Desktop bundled CLI SHA-256 | `61e3d01014af380737cff11499d7e624595869920097dff24a395d5607b8a150` |
| Separately installed npm CLI | `@openai/codex` / `codex-cli 0.147.0` |
| Provingkit research base | `ceb8780c1f211811ddb1afdafe28a4b476b152c5` |

Package identity comes from the installed desktop's
`resources/linux-package-metadata.json`; executable identity comes from
`resources/codex --version` and its SHA-256. The npm version was checked through
its own executable and package manifest, separately from the desktop executable.

## App Server controls

The desktop executable generated the following protocol with
`app-server generate-json-schema --experimental --out <scratch-directory>`.
The fields are independent:

| Interface | Field | Meaning established by the generated schema |
| --- | --- | --- |
| `thread/start` | `daybreakEnabled: boolean \| null` | Saves the initial persistent-thread choice. Omitted/null leaves it unset. Unsupported for ephemeral threads. Does not select a turn program or grant access. |
| `thread/metadata/update` | `daybreakEnabled: boolean \| null` | Saves a persistent-thread choice. Omitted/null leaves it unchanged. Does not select a turn program or grant access. |
| `turn/start` | `cyberAccessProgram` | Experimental requested treatment for the turn. Values are `standard`, `daybreakBlue`, and `daybreakRed`. Omission preserves automatic behavior. Authorization and model-tier restrictions remain server-owned. |
| `model/list` result model | `availableAccessPrograms.cyber` | Caller-specific accepted explicit program selections. A null `availableAccessPrograms` means the catalog did not supply that metadata. |
| `thread/read` result thread | `daybreakEnabled`, `model` | Saved toggle and model metadata. These do not by themselves prove the executed turn's cyber program. |

Primary source identifiers are generated `v2/ThreadStartParams.json`,
`v2/ThreadMetadataUpdateParams.json`, `v2/TurnStartParams.json`,
`v2/ModelListResponse.json`, and `v2/ThreadReadResponse.json`. Their owning public
protocol documentation is the [OpenAI App Server README](https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md).
Experimental API use requires the client's experimental capability opt-in, as
described there; that is distinct from entitlement to Daybreak.

The generated `Turn` response object contains status, items, timing, errors, and
identifiers, but no `cyberAccessProgram` field. A successful `thread/start` or
`turn/start` response therefore cannot alone establish the requested treatment.
The desktop's internal conversation representation retains
`turn.params.cyberAccessProgram`; its `getDaybreakInheritanceSource` method reads
that value alongside the saved choice and model. This is source evidence about
client state, not an assertion that an accessible public reader exposes it.

The public [CLI Daybreak resolver](https://github.com/openai/codex/blob/main/codex-rs/exec/src/daybreak.rs)
resolves a turn program using model access-program metadata. The
[Responses request representation](https://github.com/openai/codex/blob/main/codex-rs/codex-api/src/common.rs)
uses a separate `access_programs.cyber` value, including `daybreak_blue` for
Daybreak Blue. Those are source contracts, not evidence that this account or a
particular completed turn received the program.

## First-turn Daybreak selection

Daybreak can be selected for a thread's first turn. An exact-ID read-only check
of the original operator-selected Daybreak conversation found one persisted
`turn_context`: its first and only recorded turn used `gpt-6-sol`, `ultra`, and
`cyber_access_program = daybreak_blue`. Its session metadata contained no fork
origin. This existing observation establishes first-turn behavior on the desktop;
it is separate from the Advisor's later child-dispatch experiment.
The retained field-only record `daybreak-first-turn-observation.json` has
SHA-256 `7e6fc0c4fcef698e3c18b6500070db32e6c324f2e838586e49d623b6a777a7d2`.

The generated App Server protocol separates empty-thread creation from model
execution. A persistent `thread/start` accepts `model: "gpt-6-sol"` and
`daybreakEnabled: true`, with no prompt or model turn in that operation. Its
returned thread ID can then be used in the first `turn/start`, with the desired
input, model, effort, and `cyberAccessProgram: "daybreakBlue"`. No preliminary
ordinary-model turn or fork is required by those protocol shapes. The saved
choice and explicit turn program remain separate, and access checks still
apply. Sources: generated `v2/ThreadStartParams.json`,
`v2/ThreadStartResponse.json`, and `v2/TurnStartParams.json`.

The desktop manager implements this ordering. Its `x0.createConversation`
attaches the initial choice to supported persistent `thread/start` requests;
`IX` saves the choice before preparing a first turn. With empty input and no
tool output or attachments, `IX` instead returns
`firstTurn.status: "not-requested"`. Sources: the installed
`.vite/build/early-bootstrap-45-628adb74a9c47df1.js`, UTF-8 byte `1146613`
(initial choice on thread creation), `1045507` (`IX`), and `1048620`
(empty-input branch and first-turn preparation); its fingerprint is below.

The remaining discovery gap is an externally callable route that creates an
empty chat or selects Blue before the first turn from this ordinary Advisor. The
inspected Unix IPC registration exposes owner discovery and follower operations
on existing conversations, with no creation or generic App Server request
handler identified. The native `create_thread` wrapper creates and starts the
first turn together and rejects explicit Daybreak fields. Raw `thread/start`
must not be assumed to work as a method on the desktop IPC socket. Sources:
the `dQ` registration and native handler cited below. First-turn support is
established; fresh-thread creation through the Advisor's tested IPC entry point
has not been established. Native creation followed by an explicit second turn
is verified in the next section.

## Fresh worker bootstrap

The ordinary Advisor called native `create_thread` directly with this request:

```json
{
  "model": "gpt-6-sol",
  "title": "Fresh Daybreak worker bootstrap probe · 2026-11-06",
  "target": {
    "type": "projectless",
    "directoryName": "daybreak-fresh-bootstrap-probe-20261106"
  },
  "prompt": "Use no tools and do no other work. Reply with exactly this single line: DAYBREAK_FRESH_CREATION_20261106"
}
```

`thinking` was omitted. This call returned a new local thread ID. Its first turn
completed the exact sentinel, with `gpt-6-sol` and `medium` recorded and no
`cyber_access_program` field. Readback found one session record and no fork
origin. There was no executed tool call in the first turn; its native delegated
input was represented as a function-call output.

After that terminal, the Advisor used the returned ID with the existing
follower IPC:

1. Discover its owner and read its model settings.
2. Call `thread-follower-update-daybreak` with `daybreakEnabled: true` and read
   the saved setting back.
3. Call `thread-follower-start-turn`, using the returned child ID as both
   `conversationId` and `request.threadId`, with `context: {}` and this request:

```json
{
  "threadId": "RETURNED_CHILD_ID",
  "model": "gpt-6-sol",
  "effort": "medium",
  "cyberAccessProgram": "daybreakBlue",
  "input": [{
    "type": "text",
    "text": "Use no tools and do no other work. Reply with exactly this single line: DAYBREAK_FRESH_EXPLICIT_BLUE_20261106",
    "text_elements": []
  }],
  "collaborationMode": {
    "mode": "default",
    "settings": {
      "model": "gpt-6-sol",
      "reasoning_effort": "medium",
      "developer_instructions": null
    }
  }
}
```

The matched start response returned a turn ID. That exact turn completed the
second sentinel, used no tools, and persisted `gpt-6-sol`, `medium`, and
`daybreak_blue`. Both terminals were observed within the 120-second
request bound. No retry or interrupt occurred. The child was idle afterward,
its saved choice was true, and the ordinary Advisor's saved choice remained
unset. The creation and follower calls used the already-running desktop manager;
no server was started.

For a worker request that permits a preliminary harmless turn, this supplies a
tested creation path without a fork. Keep the preliminary turn free of task
work, and place the authorized worker task in the explicit Blue request. Match
its returned turn ID and observe its terminal before accepting the result. A
caller that requires Blue on the first turn still needs the separate empty-create
or eligible-inheritance path. Do not substitute a native continuation based only
on the saved toggle; the next section records why that is unqualified on the old
probe.

This is a recipe for the observed internal interface and package, not an
installed automation or public compatibility contract. A maintained caller must
bind its own authority, admission, request, version, and terminal observation.

Retained runtime evidence:

- `fresh-bootstrap-native-observation-20261106.json`, SHA-256
  `5214ebe76c445bef1b5bc0f19642618a75a9a3a8ce8862c0638ea137e0822f2c`.
- `fresh-bootstrap-context-verification-20261106.json`, SHA-256
  `f48c80836d62aa5797cf29b385d29f50d1ae47680716d58c4247597c6e46734e`.
- `fresh-bootstrap-ipc-20261106.jsonl`, SHA-256
  `cc362a6811aad1ff7caedfcf8d1e987494300a1e93a1266095c3c5a9927c0cad`.

## November 6 native creation observation

A bounded native continuation asked the enabled probe chat to call
`create_thread` once with `model: "gpt-6-sol"`, `thinking: "medium"`, and a
no-tools sentinel prompt. The continuation completed. Its single creation call
returned this error before creating a chat:

```text
create_thread could not validate reasoning effort "medium" for model "gpt-6-sol". Use a model and reasoning combination listed in the tool description, or omit thinking.
```

No child ID was returned, and the caller did not retry. The wrapper lacked a
model-catalog entry with which to validate the requested effort; this does not
establish that `medium` is unsupported. It is separate from the earlier strict
schema rejection of explicit Daybreak fields. Omitting `thinking` permits
continuation when the catalog is unavailable; if a returned catalog lacks
`gpt-6-sol`, the wrapper instead rejects the model. Neither case qualifies fresh
Daybreak creation.

The continuation's persisted context recorded `gpt-6-sol` and `medium`, with no
`cyber_access_program` field. A targeted snapshot from the live manager recorded
`daybreakEnabled: true` and `daybreakProgramPropagationEnrolled: false`. The saved
toggle therefore did not establish an explicit Blue request on that native
continuation. The missing field does not establish provider-side treatment.
The earlier explicit follower-IPC request and completed Blue turn remain valid.

The native creation helper (`eYlV.Nw`) can carry a calling chat's saved choice,
model, and program into fresh creation and first-turn preparation. Its `Q`
helper requires propagation support, source enrollment, a release gate, and the
target capability. A saved toggle alone is insufficient. Because this probe
chat was observed unenrolled, another inheritance attempt from it would not
test the eligible path.

Source inspection identifies a renderer helper (`eYlV.Cn`) that supplies empty
input to the existing manager. Successful creation through that path returns
`firstTurn.status: "not-requested"`; this investigation has not invoked it.
The existing app-host service exposes that manager through
`appServerManagers.open("local").manager.startConversation`. This service uses
trusted Electron MessagePort RPC. It is not a method on `ipc/ipc.sock`; no
externally callable adapter to this empty-creation helper has been established.
A whitespace native prompt does not reach the empty branch: delegated creation
still supplies a text envelope or a non-null tool output.

Retained runtime evidence:

- `fresh-first-turn-create-response-20261106.json`, SHA-256
  `62300814576a9e7a02bc39884fe99098d10b46690d8a998e8529d0e6c5b6ddc9`.
- `fresh-first-turn-attempt-1-20261106.json`, SHA-256
  `9b50c3df9d5184bdc58be2feca606adc763e664ff42dea5a5aa5303530f922b0`.
- `fresh-source-stream-selection-20261106.json`, SHA-256
  `4d7d202508b986184f8b2d505cb8ed4c32458cef89f408dfcff510f14806afec`.

These findings distinguish three boundaries: explicit follower-IPC turns are
verified; native selection through saved settings is not qualified on the old
probe; first-turn Blue selection from the ordinary Advisor remains unresolved.
They do not justify waiting solely for the advertised schema to change.

Primary source: installed `webview/assets/async/105345.737be374bd.js`, UTF-8
bytes `2928` (empty helper), `3297` (native helper), `6812` (inheritance),
`8656` (creation), and `19300` (feature check), SHA-256
`47ccdd168f7772ad28751029406fb67a463d1a483a2cbe9f581f4b5772c6e382`.
Manager source: `early-bootstrap-45-628adb74a9c47df1.js`, bytes `633947`
(manager facade), `1524370` (manager service), `4152448` (app-host creation),
and `4530111` (MessagePort registration), with the fingerprint below.

## Picker-source fork eligibility observation

An authorized same-directory fork of the original picker-created Daybreak chat
returned `status: "created"` and complete synchronization. The fork's settings
read returned `gpt-6-sol`, `ultra`, and `daybreakEnabled: true`. Its targeted live
manager snapshot contained `daybreakProgramPropagationEnrolled: false`.

No model turn was submitted. The fork's own rollout contained zero
`turn_context` records; native readback showed it idle with only the source's
inherited completed turn. The original rollout's bytes and hash remained
unchanged, its model and saved choice stayed `gpt-6-sol` / true, and the ordinary
Advisor remained `gpt-6-astra` / unset. Fork creation and the targeted read
completed within the admitted 30-second bound, without a retry.

This fork cannot satisfy the enrollment prerequisite for native Daybreak
inheritance. It does not establish the original chat's enrollment. The desktop
fork handler derives the child's flag from `rg(forkResponse.thread)`, rather than
copying the source flag. `rg` returns true only for an explicit valid true;
false, an absent field, or an invalid field normalize to false. This observation
does not distinguish those underlying response cases or prove that the server
preserves enrollment when forking.

No follow-on inheritance model test was run from this unenrolled fork. The
verified two-turn fresh-worker bootstrap remains available. Selecting Blue on
the first turn from an ordinary Advisor still requires a qualified caller to
the existing empty-create helper or another eligible creation path.

Primary source: installed `early-bootstrap-45-628adb74a9c47df1.js`, UTF-8 bytes
`964084` (fork path), `969219` (child enrollment assignment), and `71209`
(enrollment normalization), with the fingerprint below. Retained evidence:

- `fresh-picker-fork-observation-20261106.json`, SHA-256
  `ce9997c4e30a3234c2c3962526180f06f054991a92af90eab1480293e1492b9e`.
- `fresh-picker-fork-selection-20261106.json`, SHA-256
  `ed2f2355f3a4ed94ddc82a4e7f05d70b3469ab11079a31286ae24d047844efc2`.
- `fresh-picker-fork-preservation-20261106.json`, SHA-256
  `50d00c313d1aaac6a316449d2bea0b1496a565de12e4b750e9911880af51bc18`.
- `fresh-picker-fork-native-readback-20261106.json`, SHA-256
  `91acfa3aa26dcf2859cf9bd3fdf898ff46a90a69540a6e56afb246225b1626d1`.

## Desktop thread tools and existing-app IPC

The native `create_thread` tool rejected an invocation with `model: "gpt-6-sol"`,
`thinking: "medium"`, `daybreakEnabled: true`, and
`cyberAccessProgram: "daybreakBlue"`. It returned `isError: true` and
`create_thread received invalid arguments.` No thread was created and no model
turn reached the App Server through that attempt. The retained record
`daybreak-explicit-wrapper-probe-20261105.json` has SHA-256
`105a3863f5489657f1aa9d253744677ba075f81a38ed0fffd3ddaf2171fc7b17`.

The installed handler's `nX` strict-object schema accepts `model` and `thinking`
and excludes the two Daybreak fields. Its `n4` `safeParse` failure path returns
the observed error before thread creation. The `codex-app-tools` MCP server
forwards arguments to that handler; the handler, rather than that forwarder,
rejects the extra fields. [Desktop handler source][ipc-handler]

The separately documented `app-server proxy --sock <socket-path>` needs an App
Server control listener. The default daemon-version query failed because that
control socket did not exist. Later process inspection identified the running
desktop's child App Server without explicit listen/socket arguments and found
desktop IPC and app-tools listeners owned by the desktop process. Starting
another App Server would test a different process. The desktop IPC route below
uses the existing manager; it does not take over the child process's standard
input or output.

A bounded read-only connection to the existing desktop IPC listener completed
initialization, owner discovery, and targeted model-settings retrieval. This
established the route to the existing manager. The subsequent isolated explicit
turn completed through the same desktop IPC mechanism, as recorded below.

The installed IPC implementation is a first-party internal interface used by
desktop clients. It is versioned, but no public external-client compatibility
contract was established. The generated App Server schema and public App Server
README do not document this desktop IPC envelope. Its owning sources are the
installed `app.asar` modules listed below. [IPC framing][ipc-framing],
[client and routing][ipc-client], [method versions][ipc-versions]

### Observed protocol and source-derived calls

The existing endpoint is the `ipc/ipc.sock` socket under the active Codex home.
Messages contain a four-byte unsigned little-endian UTF-8 JSON byte count followed
by the JSON payload. This is neither newline-delimited JSON nor the App Server's
JSON-RPC envelope. The read probe checked the peer's operating-system UID against
the caller's UID. [IPC framing][ipc-framing]

Requests have `type: "request"`, a unique `requestId`, `sourceClientId`, `version`,
`method`, `params`, and `timeoutMs: 5000` in this probe. Initialization uses
`sourceClientId: "initializing-client"`
and returns the client ID for later requests. Owner discovery returns
`handledByClientId`; subsequent calls target that owner with `targetClientId`.
Local follower calls omit the outer `hostId`: supplying it changes the expected
follower-method version. [Client and routing][ipc-client],
[method versions][ipc-versions]

| Method | Local version | Parameters and result relevant to this probe |
| --- | --- | --- |
| `initialize` | `0` | `{clientType:"desktop"}`; returns `result.clientId`. |
| `thread-owner-discovery` | `1` | `{hostId:"local",conversationId}`; returns the owner in `handledByClientId`. |
| `thread-follower-read-model-settings` | `1` | `{conversationId}`; returns `result.settings`, including model, reasoning effort, saved Daybreak choice, and thread source. |
| `thread-follower-update-daybreak` | `1` | `{conversationId,daybreakEnabled:true}`; persists the choice through `thread/metadata/update`, then returns `result.ok`. It starts no turn. |
| `thread-follower-start-turn` | `2` | `{conversationId,turnStart:{request,context}}`; calls the existing manager's `startTurn`; a successful matched IPC response carries the turn ID at `result.result.turn.id`. |
| `thread-follower-interrupt-turn` | `4` | `{conversationId,mode:"user-stop",expectedTurnId}`; the expected-turn variant is version `4`. The no-expected-turn variant is version `3`. |

The turn ID path follows the manager's unchanged App Server response, the
follower handler's `{result: response}` wrapper, and the outer IPC `result`
wrapper. The prepared client's receipt stores the full matched response under
`response`, so its path is `response.result.result.turn.id`. This is the
source-derived success shape and matches the successful explicit-turn response. [Follower handlers][ipc-manager], [client and routing][ipc-client]

The handler requires ownership of the identified conversation before routing a
follower action. A probing client can decline incoming discovery requests with
`{type:"client-discovery-response",requestId,response:{canHandle:false}}` and
discard unrelated broadcasts. [Client and routing][ipc-client],
[follower handlers][ipc-manager]

### Completed isolated explicit selection

The probe forked the existing harmless legacy seed through native `fork_thread`,
then changed only the resulting child. Both the ordinary Advisor and the seed
were explicitly denied as mutation targets in the throwaway client. Four client
invocations—child read, child enable, child start, and final Advisor read—exited
with code `0`.

The child's saved choice was set and read back as `true`. The single turn used
this request inside `turnStart`, alongside `context: {}`:

```json
{
  "threadId": "CHILD_UUID",
  "input": [{
    "type": "text",
    "text": "For this bounded invocation probe, use no tools and do no other work. Reply with exactly this single line: DAYBREAK_EXPLICIT_PROGRAM_PROBE_20261105",
    "text_elements": []
  }],
  "model": "gpt-6-sol",
  "effort": "medium",
  "cyberAccessProgram": "daybreakBlue",
  "collaborationMode": {
    "mode": "default",
    "settings": {
      "model": "gpt-6-sol",
      "reasoning_effort": "medium",
      "developer_instructions": null
    }
  }
}
```

The fork initially exposed `gpt-6-sol` with `ultra` reasoning. The request bound
both `gpt-6-sol` and `medium` in the top-level fields and in
`collaborationMode.settings`; the newly executed turn recorded `medium`.
`daybreakBlue` is the App Server request enum; `daybreak_blue` is the
persisted turn-context and Responses representation. The saved `daybreakEnabled`
choice is a separate metadata operation, not an extra turn-request field.

The manager copies the explicit program into its prepared request, then applies
its normal account, model-access, feature, thread-state, and permission
preparation. A client-supplied value therefore does not prove what the final turn
uses. The native `send_message_to_thread` path also enters normal preparation,
but derives the program instead of exposing it as an argument. Its model and
reasoning overrides first update the target's next-turn settings.
[Turn preparation][ipc-preparation]

The fork returned `status: "created"` and complete synchronization. It retained
the harmless legacy seed's history, so this was an isolated child rather than a
blank-history `thread/start` test. The first child settings read showed
`daybreakEnabled: null`; enabling it and reading it back established the new
choice explicitly. The desktop takes the fork's saved choice from the server's
response and separately builds inherited model/program selection.
[Fork preparation][ipc-fork]

The throwaway client allows only read, enable, start, and expected-turn interrupt
actions. Socket waits check a 20-second deadline with individual I/O timeouts
of at most five seconds; this is not a deadline for parsing, receipt writes,
the fork, or model execution. The client limits incoming data to 64 frames and
2 MiB per connection, and records the start attempt durably before sending.
A retained attempt prevents automatic resubmission.
Timeout or disconnection leaves the outcome unknown; neither retry nor interrupt
occurs automatically. Those bounds describe the research artifact, not a
reusable installed procedure.

| Runtime observation | Verified evidence |
| --- | --- |
| Existing-app initialization, owner discovery, and settings reads | Completed successfully against the existing desktop manager. |
| Isolated child creation and history boundary | Native same-directory fork of the harmless legacy seed; complete synchronization and retained source history. |
| Child saved choice | Initially null; `thread-follower-update-daybreak` returned `ok: true`; subsequent settings read returned `daybreakEnabled: true`. Final thread metadata recorded `daybreak_enabled = 1`. |
| Explicit request and response | One matched version-2 start request selected `gpt-6-sol`, medium reasoning, and `daybreakBlue`; the returned turn ID matched native terminal and persisted turn records. |
| Terminal result | Completed in `2500 ms` with exactly `DAYBREAK_EXPLICIT_PROGRAM_PROBE_20261105`; no error, tool marker, or tool item. No interrupt was invoked. |
| Newly executed turn context | `model = gpt-6-sol`, `effort = medium`, `cyber_access_program = daybreak_blue`. |
| Advisor preservation | Final IPC settings read retained `model = gpt-6-astra` and `daybreakEnabled = null`. |
| Seed preservation | Before-action and final source-digest checks matched, including the check after completion. |

The retained bounded record `daybreak-explicit-ipc-probe-20261105.json` has SHA-256
`7011010b4e97486b9dc2fe8c82531c826729102aad0229efd994a39e464d74ab`.
It contains the matched request and response, native fork and terminal records,
allowlisted persisted turn context, client exit codes, and preservation checks.
The throwaway client used for the probe has SHA-256
`c51512cea13a41b510d7450f6be841d1ae836765a30d4fbfabbb02b6a0b6b86a`.
Private thread, turn, client, and request identifiers and machine paths are
omitted here.

These observations verify Advisor-executed invocation of the separate program on
this child through the existing app's internal IPC. They corroborate the requested
and locally recorded program; no independent provider-side attestation was
obtained. Neither successful metadata update alone nor the sentinel alone would
establish that program. The terminal result and four IPC receipt hashes were
independently checked, and a separate native read confirmed completion.

This verifies one harmless turn with the frozen seed's harmless history. It does
not qualify substantive worker workloads or tool execution. The probe client is
deliberately sentinel-only; adapting real consumers and delivering reusable
product support remain migration work. No installed convention or stable raw
App Server endpoint is established by this experiment.

### Installed first-party source references

These identifiers are relative to the installed desktop `app.asar`. Offsets are
zero-based byte offsets in the unmodified UTF-8 bundle, not source line numbers.
They bind this investigation to desktop `26.1029.61003`; they are not stable API
names or public source URLs.

- <a id="ipc-handler"></a>**Desktop handler:**
  `webview/assets/async/497066.b1696673f0.js`, byte `108328` (`nX` strict creation
  schema), byte `110873` (`n4` validation), and byte `116897` (message validation).
  SHA-256 `83b7b5743a0dfe45ed3168baa6ec851b2fef174e308f6f70830fba0c6c34146c`.
- <a id="ipc-framing"></a>**IPC framing:**
  `.vite/build/early-bootstrap-824-1f55dca514436ade.js`, module `92272`, byte
  `205159`; reader `S` at byte `206643`, encoder `v` at byte `207915`.
  SHA-256 `fe9bc694a9f026e502e2b16cd9f2a01cd33fd69442e1473c847b5939449dd011`.
- <a id="ipc-client"></a>**Client and routing:**
  `.vite/build/early-bootstrap-339-305d03d30317c879.js`, `IpcClient`/`d$` at byte
  `1041927`, router registration at byte `1038637`, owner/follower registration
  `dQ` at byte `1052946`, `dX` response unwrapping at byte `1054106`, and the
  outer response envelope at byte `1047971`.
  SHA-256 `576ba781eb1d2db60d9a2815ca9c17dbf426c0d5c487afc373e830f87b6446ae`.
- <a id="ipc-versions"></a>**Method versions:**
  `.vite/build/early-bootstrap.js`, version table `i_` at byte `174646`, resolver
  `iI` at byte `175687`.
  SHA-256 `67a41ed9813ae1eced8fb394b539f625448519aa42e8ab3ff00363f176f771f0`.
- <a id="ipc-manager"></a>**Follower handlers:**
  `.vite/build/early-bootstrap-45-628adb74a9c47df1.js`, `Su` at byte `854848` and
  `applyThreadDaybreakEnabled` at byte `1117889`; the start-result wrapper is
  at byte `857670`, accepted-turn ID use at byte `1084198`, and unchanged
  recovery-wrapper return at byte `1096008`. `assertThreadFollowerOwner` at
  byte `1245263` checks stream ownership without requiring fork ancestry.
- <a id="ipc-preparation"></a>**Turn preparation:** same `early-bootstrap-45`
  bundle, `IY` at byte `1042898`, explicit program copy at byte `1067774`, `xS`
  preparation at byte `1074368`, and `Ty` at byte `1329122`.
- <a id="ipc-fork"></a>**Fork preparation:** same `early-bootstrap-45` bundle,
  `CE` at byte `964084`. Its SHA-256, shared by the preceding manager and turn
  references, is
  `b799f597bb0be309b49eac7c4e4b972f2bb8b5dd82a4e44bede43add38568820`.

[ipc-handler]: #ipc-handler
[ipc-framing]: #ipc-framing
[ipc-client]: #ipc-client
[ipc-versions]: #ipc-versions
[ipc-manager]: #ipc-manager
[ipc-preparation]: #ipc-preparation
[ipc-fork]: #ipc-fork

## Picker behavior and legacy selector

The installed desktop bundle contains separate legacy model constants
`gpt-daybreak-blue-latest` and `gpt-daybreak-red-latest`. Its model-picker helper
filters those identifiers and selects compatible models through
`availableAccessPrograms.cyber`. The helper chooses `daybreakBlue` when offered,
then `daybreakRed`; the standard choice selects `standard` when offered.
This supports the distinction between the new toggle and model selection, but
says nothing by itself about server-side retirement of the legacy identifiers.

Primary source: desktop `app.asar`,
`.vite/build/early-bootstrap-45-628adb74a9c47df1.js`, functions `rI`, `rx`, `rT`,
and `r_`. That bundled file's SHA-256 is
`b799f597bb0be309b49eac7c4e4b972f2bb8b5dd82a4e44bede43add38568820`.
The same file's `Ty`/`Tw` preparation code checks model access, thread state,
account identity, and feature conditions before preparing a program. Presence of
this code does not establish that every feature gate is enabled.

## Separate npm CLI

The installed npm CLI is `0.147.0`, older than the desktop's bundled CLI.
Its independently generated experimental schemas do not contain
`ThreadStartParams.daybreakEnabled`, `TurnStartParams.cyberAccessProgram`, or
`Model.availableAccessPrograms`. This is an observed limit of that installed
binary's schema, not a claim about all CLI versions or undocumented behavior.
Any CLI migration decision must bind the executable version and supported
interface; relying on the desktop version alone would miss this difference.

## Observed existing desktop turns

The Advisor checked only the two relevant existing threads and reported these
redacted native records on November 5, 2026:

| Existing thread | Saved choice | Persisted turn context |
| --- | --- | --- |
| Ordinary-model Advisor | `daybreak_enabled = null` | `model = gpt-6-astra`, effort `high`; no `cyber_access_program` field |
| Operator-selected Daybreak conversation | `daybreak_enabled = 1` | `model = gpt-6-sol`, effort `ultra`, `cyber_access_program = daybreak_blue` |

The evidence source is each selected thread's native `threads` metadata and its
corresponding persisted `turn_context`, obtained through an exact-ID read-only
lookup and a field whitelist. Private thread identifiers and paths are omitted.
This confirms that the new program selection is present in an actual desktop
turn while the Advisor remained ordinary-model. Those pre-existing records alone
did not establish worker dispatch; the completed explicit child probe above
supplies separate dispatch evidence.

## Completed legacy dispatch probe

Dispatch executed one harmless new-thread probe through the native
`create_thread` tool after receiving separate operator authorization. The planned
Advisor-executor correction reached Dispatch after that invocation. The Advisor
did not execute it, and no second probe was run merely to change the actor.

The Advisor independently checked the selected calling and probe threads. The
redacted records were:

| Thread | Saved choice | Persisted turn context |
| --- | --- | --- |
| Dispatch caller | `daybreak_enabled = null` | `model = gpt-6.1-terra`, effort `low`; no `cyber_access_program` field |
| Isolated probe | `daybreak_enabled = null` | `model = gpt-daybreak-blue-latest`, effort `medium`; no `cyber_access_program` field |

The native `wait_threads` result reported terminal completion and the exact
response `DAYBREAK_DISPATCH_PROBE_20261105`, with no tool marker in the observed
turn. The evidence consists of that native terminal result and the Advisor's
exact-ID, read-only metadata and turn-context checks. Private thread identifiers
and local paths are omitted.

This establishes that an ordinary-model parent used native thread creation to
run the legacy selector successfully in the observed environment. It is evidence
for a temporary legacy dispatch route through Dispatch. It does not establish
Advisor-executed dispatch, invocation using the new program parameter, or a
separate cyber-treatment echo from the provider. The absent
`cyber_access_program` field must remain absent in the evidence account; it
cannot be filled in from the model name.

## Provingkit consumers

At the research base, the active route begins in
[`choosing-agent-models`](../../../plugins/rolecasting/skills/choosing-agent-models/SKILL.md)
and its
[Daybreak routing reference](../../../plugins/rolecasting/skills/choosing-agent-models/references/daybreak-routing.md).
The reference frames routing around an exact model selector and separately
inventories native subagents, peer or sibling threads, Codex launch surfaces,
permitted account-home routes, and cross-harness invocation. Each remains a
separate capability question.

The maintained
[`daybreak_account.py`](../../../plugins/rolecasting/skills/choosing-agent-models/scripts/daybreak_account.py)
already checks `availableAccessPrograms.cyber` for `daybreakBlue` in
`exposed_model`. That discovery support does not itself perform a Daybreak turn.
The linked catalog and record helpers, tests, evaluation fixtures, and validators
need to be assessed with the invocation contract; they cannot be migrated safely
by replacing a model string alone.

The `gpt-daybreak-blue-latest` passage in
[Mergecraft developer guidance](../../../plugins/mergecraft/DEVELOPING.md)
records selected historical experiment results: 87 of 87 candidate judgments
against 63 of 87 baseline judgments. It is evidence about those runs, not an
active instruction selecting the model. Preserve the recorded selector and its
pinned experiment evidence when changing current invocation guidance.

## Verified route and remaining scope

The installed desktop App Server supports a program parameter separate from
model selection. The native `create_thread` attempt rejected that parameter;
the isolated explicit IPC probe then completed successfully through the existing
manager while preserving the ordinary Advisor and original seed. This settles
the bounded desktop invocation question for the observed package and account.

The [initial dispatch decision](https://github.com/nisavid/provingkit/issues/872)
and [migration map](https://github.com/nisavid/provingkit/issues/871) track the
decision and its consumers. The
[native-dispatch follow-up](https://github.com/nisavid/provingkit/issues/876)
retains the separate exposed-wrapper question. This successful internal route
does not establish a public external-client compatibility contract, a maintained
installed procedure, or support for arbitrary models or accounts.

The [surface research](https://github.com/nisavid/provingkit/issues/873),
CLI, and cross-harness decisions retain their own version, account, authority,
and capability checks. There is no basis for a universal legacy deprecation
claim or a blanket replacement of historical selectors. This research note
records a completed bounded experiment; it does not authorize further probes,
account changes, or product changes.

## Source fingerprints

The desktop-generated experimental schemas have these SHA-256 values:

| Generated file | SHA-256 |
| --- | --- |
| `v2/ThreadStartParams.json` | `80a40a7fac15b4bf70efb7f893fb353acc0a0d30c68f54aee4f01923deca85de` |
| `v2/TurnStartParams.json` | `c7483aee79757d260c4fc1bb5c68b1a8d6f72846388e9f1e88d6f76f423287c8` |
| `v2/ModelListResponse.json` | `2fb387a2ed258fc74258828ea342d68f89ce4e8e22cd0329ca59d2b423f9108b` |

The source artifacts bind the observed invocation to the installed desktop
version. The native-wrapper rejection, completed legacy probe, and successful
explicit IPC probe retain their distinct evidence and scope.
