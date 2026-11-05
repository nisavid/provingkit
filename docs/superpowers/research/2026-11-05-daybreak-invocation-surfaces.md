# Daybreak invocation surfaces

The installed desktop App Server supports a Daybreak program selection separate
from the model. The exposed Codex app thread tools do not expose that selection.
Direct native-tool dispatch from an ordinary-model parent using the legacy
selector completed in one isolated probe. Explicit new-method dispatch into the
same running App Server remains unverified. A saved Daybreak toggle is not
evidence that a turn ran with Daybreak treatment.

This research records source, schema, and bounded runtime observations made on
November 5, 2026. It supports the
[Daybreak invocation migration map](https://github.com/nisavid/provingkit/issues/871)
and its
[initial dispatch decision](https://github.com/nisavid/provingkit/issues/872). It does not establish migration, qualification, publication, installation,
or release acceptance.

## Scope and evidence

The first decision is whether an ordinary-model Advisor can create a separate
Daybreak worker through its existing desktop App Server. The Advisor must remain
usable without Daybreak access. Later decisions cover the CLI and cross-harness
consumers independently; support on one surface does not establish support on
another.

The research used the installed first-party desktop distribution and its schema
generator. No new model turn, account change, server start, or thread mutation was
performed by the source researcher. Dispatch separately executed one authorized
legacy-route probe. The Advisor inspected the specifically identified threads
through read-only database lookups and allowlisted turn-context fields, as
recorded below. Schema generation emitted a warning that it could not create
PATH aliases on the read-only filesystem, then completed successfully. The observed interfaces are identified below so a later investigator
can regenerate the schemas from the same binary.

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

## Desktop thread tools and transport

The live `create_thread` tool schema accepts `model` and `thinking`, with no
`daybreakEnabled` or `cyberAccessProgram` parameter. The
`send_message_to_thread` schema still lists `gpt-daybreak-blue-latest` as a model
override. These observations establish the wrapper's advertised interface, not
server rejection of the new protocol or universal retirement of the old model.

The installed `codex-app-tools` MCP server forwards `tools/list` and `tools/call`
to the desktop's tool bridge. Its inspected implementation does not offer a
public arbitrary App Server request tool. Source: desktop bundled
`plugins/codex-app-tools/server.mjs`, `createCodexAppToolsMcpServer` and
`NativePipeClient.request`.

The desktop executable documents `app-server proxy --sock <socket-path>` as a
way to connect to a running App Server control socket. The read-only
`app-server daemon version` check failed because the default control socket did
not exist. A bounded local listener inventory found desktop IPC and app-tools
listeners but did not identify an App Server control listener. This observation
is limited to the checked default endpoint and visible local listener inventory;
it does not prove that every possible same-server route is unavailable.

Starting another App Server would test a separate process and would not answer
the direct intra–App Server question. Connecting to an undocumented internal
socket or altering the Advisor's saved settings was not attempted.

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
turn while this Advisor remains ordinary-model. It does not verify that the
Advisor can dispatch a new worker through that interface.

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

## Deferred new-method verification

The initial source question has an answer: the installed desktop App Server has
a program parameter separate from model selection, while the exposed native
thread-creation tool lacks controls for it. The existing operator-selected turn
contains the new program in persisted context. The bounded legacy probe supplies
a working temporary dispatch observation, with the treatment-evidence limits
above. There is no basis for a universal deprecation claim or a blanket
replacement of legacy selector references.

The [initial dispatch decision](https://github.com/nisavid/provingkit/issues/872)
records this bounded result. The
[migration map](https://github.com/nisavid/provingkit/issues/871) retains
[a deferred native-dispatch decision](https://github.com/nisavid/provingkit/issues/876)
for when the native wrapper exposes the controls or a supported transport into
the same running App Server becomes available. Starting a separate server would
answer a different question.

Once such a route exists, a separately authorized isolated probe can bind
caller-specific model discovery, an advertised program, and one harmless turn
with explicit selection. Its evidence needs the requested model and program,
returned thread and turn identifiers, saved-toggle readback, terminal
disposition, and any model reroute or verification notification. A persisted
turn-context record can corroborate the selected program, as the existing
operator-selected turn demonstrates. Neither metadata alone nor successful
thread creation substitutes for per-turn evidence.

Until then, implementation planning can distinguish available surfaces from
those awaiting a control. The CLI and cross-harness decisions retain their own
version, account, authority, and capability checks. This note does not authorize
another probe or product changes.

## Source fingerprints

The desktop-generated experimental schemas have these SHA-256 values:

| Generated file | SHA-256 |
| --- | --- |
| `v2/ThreadStartParams.json` | `80a40a7fac15b4bf70efb7f893fb353acc0a0d30c68f54aee4f01923deca85de` |
| `v2/TurnStartParams.json` | `c7483aee79757d260c4fc1bb5c68b1a8d6f72846388e9f1e88d6f76f423287c8` |
| `v2/ModelListResponse.json` | `2fb387a2ed258fc74258828ea342d68f89ce4e8e22cd0329ca59d2b423f9108b` |

The source observations and completed legacy probe resolve the bounded seed
research question. New-method dispatch and the remaining invocation surfaces
retain separate acceptance evidence and open follow-up decisions.
