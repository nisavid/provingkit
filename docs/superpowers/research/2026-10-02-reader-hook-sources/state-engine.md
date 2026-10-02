# Public RC engine source addendum

**DONE_WITH_CONCERNS.** The public RC artifact establishes concrete Code-state getters and hook paths. It does not establish the selected live executor, a complete receiver-state snapshot, or runtime qualification.

## Source identity and inspection boundary

I inspected embedded source as data in the [public Claude Code RC artifact](https://downloads.claude.ai/claude-code-releases/rc/16cbb4ddeeb473f57fd8d5b713764903d7928e66/2.1.284/linux-x64/claude.zst).

The supplied identity records Desktop’s source target as version `2.1.284`, commit `16cbb4ddeeb473f57fd8d5b713764903d7928e66`. The embedded version, commit, and build time agree: `2026-09-27T04:38:16Z` (bytes `[232738801,232740720)`).

The decompressed artifact is 243,059,896 bytes. I independently recomputed SHA-256:

`dee301c3e248c62137cc15aafc2781bd5316c66720dd890d72e0054a024ce7d9`

All references below are zero-based UTF-8 byte spans into that full binary, written as `[start,end)`. Minified symbols are interpreted within their modules and linked through imports.

This is a **public Desktop source-target artifact**, not an observed live executor. Stable SDK `0.3.284` remains a separate artifact; matching version numbers do not establish byte identity with Desktop’s declared RC wrapper. I did not execute, import, install, alter, or upload the binary, inspect private receiver state, or read the prototype or another lane’s findings.

## Concrete control handlers

The initial report’s missing engine-handler evidence is now supplied for this source target.

The headless dispatcher handles shared control requests directly, with special asynchronous scheduling for selected operations. `get_context_usage` appears in the shared handler map and reaches `UQ` through its imported module (bytes `[220702850,220703750)`, `[221182050,221183000)`, and `[220671712,220674212)`). Separate headless branches implement `get_status`, `get_settings`, and `list_permission_rules`.

Availability remains connection-dependent. Those three branches reject connections selected by `$g`; that predicate considers hosted-worker state and transport persistence. Thus their presence does not prove that every SDK or remote connection can use them (bytes `[204546800,204547800)`, `[221193550,221194550)`, and `[221225050,221226950)`).

### Settings and applied values

`get_settings` reads merged settings and source records, then separately returns an `applied` object containing model, effort, advisor, and ultracode-related values. It also reports settings errors and a remote-control policy-lock reason. Under one policy-lock condition, it waits for policy-related promises before replying (bytes `[221225050,221226050)`).

This establishes a distinction the consumer must preserve:

- `effective` is merged configuration.
- `applied` contains the explicitly named runtime values.
- Neither object is a complete applied-permissions snapshot.

The model value in `applied` comes from `st()`. That resolver uses the current explicit/configured model selection and default resolution; it does not read the model of an individual API attempt (bytes `[200476500,200478230)`).

### Live Code permission rules and directories

`list_permission_rules` passes the engine’s current `toolPermissionContext`, session `originalCwd`, settings-source reader, and settings-error reader to `buildPermissionRulesWireState` (bytes `[221226535,221226950)`).

The builder enumerates allow, ask, and deny rules through the same `_L`, `gh`, and `Qd` helpers used for applicable Code rules. Its source list includes session and command rules, tool narrowing, MCP server policy, and host credentials. `_L` applies mode-dependent filtering to allow rules; deny and ask helpers flatten their corresponding context arrays (bytes `[201860380,201862030)`).

The response includes current `additionalWorkingDirectories` with their sources, `originalCwd`, the managed-only setting, and non-warning settings errors. When managed-only rules apply, configured non-policy settings rules are additionally returned as inactive and read-only (bytes `[231927050,231928958)`).

This is stronger evidence than a defaults-only settings read. It supplies currently applicable Code rule arrays and applied additional directories, including represented server/host rule sources. It does **not** expose every runtime permission input: raw permission mode, bypass availability, filesystem or sandbox flags, separate Desktop browser grants, computer-use grants, and checks outside those arrays remain distinct. It also does not reconstruct every filtered or stripped rule from the live context.

## Account, model, and cwd semantics

### Status is a live display projection

The headless `get_status` handler supplies credentials, `Bn() ?? st()`, MCP state, and the current permission mode to `buildStatusSections` (bytes `[221193767,221194400)`). The builder obtains session ID and cwd at invocation, then formats display rows (bytes `[232758900,232759575)`).

The cwd producer `oe()` reads the current asynchronous cwd context or the global cwd, falling back to the original cwd if that read throws (bytes `[198480300,198481700)`). This closes the source-level gap for a current engine-cwd getter. Its result remains distinct from Desktop’s registered worktree identity; the status rows do not supply that complete binding.

The model row is display text. `w7r` formats the supplied model and can append previous-model information (bytes `[222917620,222918050)`). `Bn()` resolves a recognized or permitted user model pick; otherwise the handler uses `st()` (bytes `[221115200,221116200)` and `[220569836,220570300)`).

Passing permission mode into this formatter does **not** return that raw mode. The corresponding row is “Auto mode server”, formatted as enabled or disabled (bytes `[232740720,232741250)` and `[222910036,222910220)`).

### Account information remains local credential metadata

The status account rows call `o_e()`, which derives token/key source, subscription, organization, and email from credential/configuration state. Initialization builds its account object from the same producer (bytes `[200803900,200805150)` and `[221256990,221258700)`).

The async status helper named `refreshKnownDead` checks known-dead token/store state through `N1`; its name is not evidence of an authenticated account lookup. `N1` reads credential state and tests refresh-token status (bytes `[222912573,222912900)` and `[200778533,200779000)`). API-key-helper values can come from a cached helper result (bytes `[200758041,200759200)` and `[200763115,200763400)`).

Consequently, these outputs identify local credential selection and cached profile information. They do not establish which account a particular inference request authenticated.

### Context usage resolves a model; it does not inspect an attempt

Headless `contextUsageInputs` supplies messages, tools, agents, and prompt inputs, but no model. The shared handler therefore defaults to `st()` (bytes `[221137250,221138350)`, `[221140150,221140450)`, and `[220676180,220677000)`).

`UQ` captures current engine state and invokes the context analysis. That analysis derives its returned model through `Xf`, using permission mode and the supplied main-loop model; plan-mode resolution can change it. The returned `model` is that resolved value (bytes `[211588683,211589300)`, `[206637644,206638400)`, `[200484650,200485600)`, and `[206643035,206643365)`).

For `detail:"summary"`, token counting uses local estimates rather than the full counting path (bytes `[206628918,206629650)`). That makes summary a narrower observation candidate, but it does not change its model semantics.

## Hooks, fallback differences, and StatusLine

`PostModelSwitch` is driven by engine-state changes. The state observer compares resolved models when main-loop model, session model, or permission mode changes, then invokes `Wwr` if the resolved model differs. `Wwr` constructs the hook input and runs registered hooks (bytes `[213374720,213375720)` and `[207301558,207302950)`).

A fallback can instead change the query’s attempt model and `availabilityFallback` options without changing session state. That branch emits `query_model_change` and a `model_fallback` system event (bytes `[213024300,213027950)`). The headless output projection forwards `model_fallback`, while discarding the internal `query_model_change` event (bytes `[220898500,220900700)`).

Other fallback paths do update session state and can therefore trigger the session-model hook (bytes `[213011500,213012250)` and `[213017250,213018250)`). This confirms the earlier distinction: session-model hooks and getters do not cover every retry model. It does not add a requirement for interval-wide monitoring.

`CwdChanged` constructs old/new cwd fields through `nEr`. The traced shell completion path invokes it only after a successful foreground cwd change and outside a nested asynchronous cwd context (bytes `[207297100,207298050)`, `[205928000,205930750)`, and `[205965100,205966100)`). This is an event path, not an exhaustive worktree/cwd snapshot.

StatusLine’s only `new CNn` construction found is in the React UI component. Its subscription activates execution; the controller reads session cwd and builds the command payload from UI-provided inputs (bytes `[226603350,226605900)` and `[206359650,206362750)`). The headless adapter explicitly reports that it has no status row (bytes `[221137250,221138350)`). I found no headless StatusLine producer path in this artifact.

## Corrected conclusions and remaining gaps

The new source replaces uncertainty about handler implementation with specific semantics: current engine cwd and applicable Code rules/directories have concrete producers. Settings provide named applied values. Status and context usage provide different model projections. StatusLine is unsupported as a headless producer by the inspected route.

A complete qualification sample still needs the selected executor’s identity, usable access to the exact receiver query, current account authentication evidence, registered worktree binding, and remaining Desktop/server permission inputs. Separate getters also do not constitute an atomic snapshot; asynchronous results need receiver/query identity checks and a defined sampling boundary.

The inspection is complete as source research. These findings do not establish runtime qualification, transport delivery, explicit ACK, security-control acceptance, or activation.