# Daybreak controls across Provingkit invocation surfaces

Provingkit can use explicit Daybreak Blue on Codex CLI/TUI and on a directly
controlled App Server turn, but its maintained procedures do not yet qualify
either route for task work. ChatGPT Codex's native thread wrapper still exposes
model and effort rather than the new program field; native subagents inherit a
parent turn's program but cannot select one independently. Runtime evidence is
limited to the corrected desktop research's first recorded UI turn and two
harmless sentinels: one legacy-model native thread and one explicit-program turn
through the existing desktop manager. None qualifies tools, substantive
research, or a reusable dispatcher.

This note answers [issue #873](https://github.com/nisavid/provingkit/issues/873)
from static first-party source and the already accepted observations at
Provingkit commit `190c77cdd768e46adf3f157c683a3174e0a1c788`. It performed no
model or runtime probe. Configuration, entitlement, observed execution, and
qualification are separate below.

## Version boundary

- ChatGPT desktop is still `26.1029.61003`; its bundled CLI is
  `0.166.0-alpha.6`, SHA-256
  `61e3d01014af380737cff11499d7e624595869920097dff24a395d5607b8a150`.
  These values were re-read from the installed first-party package on November
  5, 2026 and match the [corrected desktop research](https://github.com/nisavid/provingkit/blob/190c77cdd768e46adf3f157c683a3174e0a1c788/docs/superpowers/research/2026-11-05-daybreak-invocation-surfaces.md#scope-and-evidence).
- The CLI selected by the current path reports `codex-cli 0.166.0`. The
  separately inspected `0.166.0` executable has SHA-256
  `2e169440d5e84fd75464c6ef96a2d19b45f9155c38aee1bc6ab632608d81087d`.
  The inspected public release is tag `rust-v0.166.0`, commit
  [`6ff1e1ca3b30fc8b914720681fcf5fe62e95f856`](https://github.com/openai/codex/tree/6ff1e1ca3b30fc8b914720681fcf5fe62e95f856).
  An older installed `0.147.0` binary remains separate and is not evidence for
  `0.166.0`; its schemas lack the new fields, as the corrected research records.
- Current public-source comparison used OpenAI Codex commit
  [`e934edd68c73da93486320c77af672a015b4514a`](https://github.com/openai/codex/tree/e934edd68c73da93486320c77af672a015b4514a)
  from November 5, 2026. It agrees with the release on the controls discussed
  here, but an unreleased main revision is not an installed-version claim.
- Provingkit consumer source was inspected at
  `190c77cdd768e46adf3f157c683a3174e0a1c788`; its underlying main base is
  `ceb8780c1f211811ddb1afdafe28a4b476b152c5`. The separate Rolecasting product
  correction in [issue #551](https://github.com/nisavid/provingkit/issues/551)
  is authoritative for naming: ChatGPT Codex uses `chatgpt-codex`; the separate
  `codex-desktop` profile is unsupported. Its reviewed correction is not yet
  published or installed, so current installed references using
  `codex-desktop` must be treated as stale evidence, not supported policy.

## Surface matrix

| Actual Provingkit consumer | Surface and inspected version | Accepted controls | Request and persisted observations | Support and disposition |
| --- | --- | --- | --- | --- |
| Rolecasting `choosing-agent-models`, dispatched through ChatGPT Codex UI | ChatGPT desktop `26.1029.61003`; bundled CLI `0.166.0-alpha.6` | UI saves a thread-level Daybreak choice and prepares a turn program from the selected model's `availableAccessPrograms.cyber`. Model, effort, saved choice, and turn program are distinct. | The first recorded operator turn persisted `model=gpt-6-sol`, `effort=ultra`, and `cyber_access_program=daybreak_blue`; the thread saved `daybreak_enabled=1`. The public `Turn` response does not echo the program. | **Observed, narrow:** a first-turn Daybreak UI execution exists. It is not a dispatcher or tool qualification. Continue to use that observation only for UI first-turn capability. Revisit after an app build change, account/catalog change, or a consumer asks for substantive/tool qualification. |
| Rolecasting through native `create_thread`, `send_message_to_thread`, fork, and wait tools | Same desktop package; live tool schemas re-read November 5, 2026 | `create_thread` and `send_message_to_thread` expose model and reasoning effort, not `daybreakEnabled` or `cyberAccessProgram`. The live continuation schema still lists legacy `gpt-daybreak-blue-latest`. Fork has no model, effort, or program field. | Native terminal status and response are observable. The legacy sentinel persisted `model=gpt-daybreak-blue-latest`, `effort=medium`, with no `cyber_access_program`; saved choice remained unset. The explicit new fields were rejected before thread creation. | **Observed, legacy-only:** the harmless legacy selector completed once. It does not prove Daybreak treatment from the model name and does not qualify task work. Keep it only as a bounded temporary route when the exact legacy selector is independently current and the consumer accepts the missing program evidence. Fresh empty-thread creation through an externally callable existing-app interface remains unresolved. Revisit when the native wrapper exposes a program field or a public existing-manager creation method. |
| Rolecasting native child adapter and harness `spawn_agent` | Live ChatGPT Codex schema (product build not exposed); OpenAI Codex `0.166.0` source for the corresponding native-child implementation | Spawn accepts model and reasoning effort but no cyber-program field. The implementation copies the parent turn's `cyber_access_program` into `SpawnAgentOptions`; it does not derive an independent child selection ([source](https://github.com/openai/codex/blob/6ff1e1ca3b30fc8b914720681fcf5fe62e95f856/codex-rs/core/src/tools/handlers/multi_agents/spawn.rs#L98-L138)). | Native events report requested/effective model and effort, child ID, status, and result, but no program echo. A child may inherit a parent program in source; no Provingkit execution observation qualifies that path. | **Source-only:** an already-Daybreak parent can source-inherit its turn program, but an ordinary parent cannot explicitly select Daybreak for a child through the current schema. Do not use inheritance as an ordinary-to-Daybreak dispatcher. Revisit when the live spawn schema exposes explicit program selection or a bounded parent-to-child inheritance probe is separately admitted and its evidence contract is accepted. |
| Rolecasting via Codex TUI | Standalone `0.166.0`, public release commit `6ff1e1c…` | `/daybreak` toggles the saved preference. The stable `cli_daybreak` feature resolves a program only after account eligibility and model-catalog support; missing catalog metadata preserves automatic behavior ([resolver](https://github.com/openai/codex/blob/6ff1e1ca3b30fc8b914720681fcf5fe62e95f856/codex-rs/tui/src/daybreak.rs), [stable feature](https://github.com/openai/codex/blob/6ff1e1ca3b30fc8b914720681fcf5fe62e95f856/codex-rs/features/src/lib.rs#L1491-L1508)). Model and effort remain separate selections. | Persistent threads save `daybreakEnabled`; turn preparation carries a `CyberAccessProgram`. The public turn object reports status, items, timing, errors, and IDs, not the program. Local turn context can retain the effective program. | **Source-only:** supported in the installed version, but no TUI execution or Provingkit qualification was run. Defer task routing until the exact account/model/effort catalog tuple and a harmless run are qualified under the maintained procedure. Revisit on binary, account, model catalog, saved-thread, or feature-state change. |
| Rolecasting cross-harness launch through `codex exec`, including `resume` and prompt-bearing `fork` | Standalone `0.166.0`, public release commit `6ff1e1c…` | Global `--cyber-access-program {standard,daybreak_blue,daybreak_red}` supplies an explicit per-turn request; `--model` and configured reasoning effort remain separate. Review rejects the flag; fork requires a prompt ([CLI definition](https://github.com/openai/codex/blob/6ff1e1ca3b30fc8b914720681fcf5fe62e95f856/codex-rs/exec/src/cli.rs#L20-L104)). With no explicit flag, new, resumed, and forked sessions can resolve the saved `daybreak` preference through the catalog; resume/fork read the saved thread choice ([execution path](https://github.com/openai/codex/blob/6ff1e1ca3b30fc8b914720681fcf5fe62e95f856/codex-rs/exec/src/lib.rs#L1034-L1272)). | The command line establishes requested configuration; catalog metadata establishes caller-specific accepted selections. JSON/terminal completion establishes execution outcome but does not echo the program. Local turn context retains `cyber_access_program`, model, and effort ([turn context](https://github.com/openai/codex/blob/6ff1e1ca3b30fc8b914720681fcf5fe62e95f856/codex-rs/core/src/session/turn_context.rs#L381-L382)). The Responses request maps Blue to `access_programs.cyber=daybreak_blue` ([wire source](https://github.com/openai/codex/blob/6ff1e1ca3b30fc8b914720681fcf5fe62e95f856/codex-rs/codex-api/src/common.rs#L29-L44)); that is not provider attestation. | **Source-only, not yet consumed safely:** Provingkit's cross-harness guidance still frames dispatch around an exact model selector and has no qualified explicit-program invocation record. For a selected account home, every initial `exec` and `exec resume` must bind the same `CODEX_HOME`; current status and harmless-probe gates still apply ([consumer contract](https://github.com/nisavid/provingkit/blob/190c77cdd768e46adf3f157c683a3174e0a1c788/plugins/rolecasting/skills/delegating-cross-agent-work/references/foreign-harness-peers.md#task-and-thread-isolation)). Do not fall back to ambient account state. Revisit when Rolecasting records binary version and explicit program and gains an admitted harmless execution check. |
| `daybreak_account.py` status refresh, the concrete directly launched App Server consumer | Provingkit `190c77cd…`; it accepts an arbitrary trusted absolute Codex executable. This host's active candidate is `0.166.0`, but the helper neither pins nor emits its version. | The helper starts `codex app-server --stdio`, initializes, reads account and rate limits, then pages `model/list`. It requires the exact model and effort and `availableAccessPrograms.cyber` containing `daybreakBlue` ([helper source](https://github.com/nisavid/provingkit/blob/190c77cdd768e46adf3f157c683a3174e0a1c788/plugins/rolecasting/skills/choosing-agent-models/scripts/daybreak_account.py#L356-L443)). It sends no `thread/start` or `turn/start`. | Its allowlisted output records observation time, freshness, binding match, authenticated state, selector exposure, ordinary usage, and capacity. It does not record executable version, request a program, create a thread, or observe execution. | **Observed procedure capability, status-only:** suitable for entitlement discovery, never execution qualification. `harmless-probe` deliberately fails before launch. Keep execution deferred. Revisit only after an authorized actuator can bind the selected home and binary, create an isolated thread, explicitly request Blue, deny task tools, preserve uncertain outcomes, and return accepted evidence. |
| A future direct App Server execution client used by Rolecasting | Protocol generated by desktop `0.166.0-alpha.6`; public `0.166.0` source | With `experimentalApi`, persistent `thread/start` accepts `daybreakEnabled`; `thread/metadata/update` changes it later. `turn/start.cyberAccessProgram` independently accepts `standard`, `daybreakBlue`, or `daybreakRed`; `model/list.availableAccessPrograms.cyber` is the entitlement/catalog check. The saved choice neither selects a turn program nor grants access ([App Server contract](https://github.com/openai/codex/blob/6ff1e1ca3b30fc8b914720681fcf5fe62e95f856/codex-rs/app-server/README.md#initial-daybreak-choice-experimental), [turn field](https://github.com/openai/codex/blob/6ff1e1ca3b30fc8b914720681fcf5fe62e95f856/codex-rs/app-server-protocol/src/protocol/v2/turn.rs#L298-L313)). | `thread/read` exposes saved choice and model. `turn/start` returns a `Turn` without the requested/effective program. A client must preserve its request and obtain separately accepted local persisted context or stronger attestation. The corrected desktop IPC sentinel observed request, terminal, and persisted context, but internal IPC is not a public compatibility contract. | **Protocol-supported; product route absent:** do not treat raw `thread/start` as a method on the desktop IPC socket, and do not start a second server as evidence about the existing manager. The temporary route is the already observed internal sentinel only; it is not reusable. Revisit when the owning workflow chooses a public direct-client process boundary and accepts its evidence and containment contract. |
| Permitted alternate account homes and foreign harness callers | Rolecasting `190c77cd…`; exact executable and account-home version vary per binding and were not inspected because this task prohibited protected catalog access and account changes | The maintained status helper can check identity, exact model/effort exposure, Daybreak Blue catalog support, usage, and capacity. `codex exec 0.166.0` can request the program explicitly, but each selected-home executable must be versioned independently. | Catalog and status are configuration/entitlement evidence only. The current helper has no harmless probe, no execution record, and no task-tool closed-world denial. No protected binding was opened in this research. | **Unavailable for task execution under the current maintained procedure:** no account-home route is genuinely runnable until its own authority, current status, exact binary/version, workspace, tools, capacity, and harmless probe pass. Preserve the legacy selector only in historical evidence and only use it prospectively if that exact route independently requalifies it. Revisit per exact tuple when any binding, identity, binary, model, effort, program catalog, capacity, workspace, tool scope, or authority changes. |

No public API or SDK row is included. A targeted inspection of Provingkit main
`ceb8780c…` found no `@openai/codex` SDK import or Responses API caller. Public
SDK support therefore would not answer a live Provingkit consumer question.

## What the evidence permits

**Configuration.** A saved `daybreakEnabled` preference, an explicit
`cyberAccessProgram`, a model selector, and reasoning effort are four separate
inputs. The explicit program requests an authorized treatment; it does not grant
one.

**Entitlement.** The caller-specific model catalog's
`availableAccessPrograms.cyber` is the relevant discovery field. Null, missing,
or empty metadata does not prove denial, and picker visibility does not prove
entitlement. Rolecasting's status helper already checks this field, but only for
the selected account-home tuple.

**Observed execution.** The corrected research establishes one UI first turn,
one native legacy-selector sentinel, and one explicit-program sentinel through
the existing desktop manager. The explicit sentinel combined the preserved
request, terminal result, and persisted `cyber_access_program=daybreak_blue`;
the legacy sentinel had no program field. Forking isolated the explicit test but
was not an interface prerequisite. The [full observation boundary](https://github.com/nisavid/provingkit/blob/190c77cdd768e46adf3f157c683a3174e0a1c788/docs/superpowers/research/2026-11-05-daybreak-invocation-surfaces.md#completed-isolated-explicit-selection)
must remain intact.

**Qualification.** None of those observations qualifies substantive research,
tool use, cross-account dispatch, native-subagent inheritance, TUI, `exec`, or a
reusable direct client. A successful response or sentinel alone does not prove
the program. No provider-side treatment attestation was identified.

Historical `gpt-daybreak-blue-latest` selectors must remain unchanged wherever
they identify the experiment that actually ran, including Mergecraft's 87/87
candidate result. Their historical validity neither proves current support nor
authorizes a blanket migration. Conversely, the new controls do not establish
universal legacy deprecation.

## Maintained-procedure proposal

Existing equipment already owns this method, so no new skill is warranted.
After the product decision, change the maintained Provingkit source rather than
an installed plugin copy:

1. Extend `choosing-agent-models/references/daybreak-routing.md` with a
   surface-versioned control record: product profile, binary/build identity,
   account-binding observation, model, effort, requested program, saved choice,
   catalog entitlement, terminal outcome, persisted program observation, and
   qualification state. Continue to keep configuration, entitlement, execution,
   and qualification separate.
2. Extend `daybreak_account.py`'s status schema to capture the selected Codex
   executable's product version and an explicit allowlisted Blue-program
   exposure field. Do not add execution to the status operation.
3. Add a separately reviewed execution actuator only if its chosen surface can
   enforce the existing account, workspace, task-data, tool, single-admission,
   uncertain-outcome, and cleanup contracts. CLI `exec` is the smallest public
   existing mechanism; a direct App Server client offers finer lifecycle control
   but requires more owned transport and evidence machinery.
4. Update `delegating-cross-agent-work` to invoke the reviewed procedure before
   every initial dispatch and continuation, record the producing source revision,
   and reject stale evidence after a tuple change. Publish the `chatgpt-codex`
   naming correction from #551 before treating the downstream profile as
   corrected.

The proposal belongs in the Provingkit source repository's Rolecasting skill and
references. Plugin caches and installed projections remain immutable. Downstream
consumers should load `choosing-agent-models`, record the reviewed producer
revision, and verify its completion result before dispatch; a status record alone
must never satisfy an execution prerequisite.

## Evidence limits and decisions for Lead

- This worker's system context identifies the model only as **GPT-5**. No
  reasoning-effort value is exposed. No separate cyber-program field is exposed
  for this worker, so none is inferred from its model name or task assignment.
- The ChatGPT Codex product build for this worker's native-subagent controller is
  not exposed. The live tool schema is current evidence for fields, while public
  Codex `0.166.0` source is only implementation correspondence, not proof of the
  hosted build.
- No protected account-binding catalog, authentication state, task data, or
  topology file was inspected. In particular, no Tricritical
  `references/topology.json` or copy was sought.
- Decide which public route should become the first maintained actuator:
  `codex exec` with its explicit flag, or a direct App Server client. The former
  is smaller; the latter offers explicit thread metadata and lifecycle control.
- Decide whether local persisted turn context plus a preserved request and
  terminal result is sufficient execution evidence, or whether migration must
  wait for stronger provider-owned attestation.
- Decide whether native child inheritance is an acceptable same-program
  continuation after qualification, or whether every child must wait for an
  explicit spawn field.
- Fresh empty-thread creation through the already running desktop manager remains
  unresolved. A public wrapper field or public manager endpoint is the missing
  fact; another internal-IPC sentinel would not settle compatibility or
  maintainability.
