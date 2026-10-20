# A bounded startup diagnostic for the compatibility observation

This proposal identifies a current installed Codex candidate and the smallest next observation that could explain startup failure: one app-server start, stopping after initialization or the first failure, with narrowly selected filesystem-operation metadata. Full profile discovery follows only after startup is understood.

The proposal is prepared, not executable or approved. Its missing equipment is explicit: a pinned trace backend and a locally qualified bounded collector. No runtime, tracer, native author, Jev assessment, or model comparison was started during this preparation. No permissions or live configuration changed.

## Why this advances System One research

The compatibility workload asks an ordinary agent to add opt-in JSON to an inventory report while preserving its existing consumers. A native baseline can reveal a real missed obligation or review step worth comparing with deterministic checks or a narrow Jev assessment. Startup failure currently prevents observing that baseline. This diagnostic addresses that obstacle; it supplies no evidence that a System One component is useful or economical.

Two independent preparation workers examined runtime routing/interfaces and startup diagnostics. Their original handbacks are preserved. The coordinator then located the current Vite+ package and checked its corresponding public source, separately from those first handbacks. Both workers completed and their controllers exited. The coordinator supplied a malformed status-observation shape to the recording adapter before closing those controllers; the adapter rejected it. The original research and observed closures remain evidence, but no successful adapter result record is claimed. Final proposal review is separate.

## Selected candidate and interfaces

The local Vite+ registry names `@openai/codex` 0.163.0. Its installed Linux x64 executable is 296,865,480 bytes with SHA-256 `399ff69c431c066e40de318fba45c2b07f45a76b19939d247ee4828fc70c4215`. The proposal selects that executable directly, by absolute path in the private binding, rather than relying on the secret-backed PATH launcher. This preserves the collector's existing direct-executable design. It does not establish what the wrapper would ultimately execute, reproduce the historical 0.162.1 run, or attest a reproducible binary build.

The former 0.162.1 executable is absent. A separate npm installation declares 0.147.0, but it is not selected. Official tag `rust-v0.163.0` resolves to commit `83086188ae0614bd882818ff1aa23f3194962012`. The retained source manifests record 24 downloaded public files and their digests.

The source declares `--no-daemon`, `app-server --stdio`, and `--strict-config`; the app-server branch selects stdio and passes strictness into startup. This is source correspondence, not an observed parser pass. See [the no-daemon declaration](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/tui/src/cli.rs#L87-L89), [app-server declarations](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/cli/src/main.rs#L571-L594), and [app-server dispatch](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/cli/src/main.rs#L1237-L1295).

The collector's ten feature names are present in the selected feature registry. Presence is not enforcement: `plugin_hooks` is a removed compatibility flag whose value is ignored. Actual omission behavior remains an observation obligation, including the `hooks` disable and cooperative author overlay. See [feature parsing](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/features/src/lib.rs#L686-L695) and [feature registry](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/features/src/lib.rs).

| Existing discovery request | Source correspondence | Next use |
| --- | --- | --- |
| `initialize` | `clientInfo` plus optional capabilities; response requires `userAgent`, `codexHome`, `platformFamily`, and `platformOs` | Sole request in the proposed startup diagnostic |
| `model/list` | Cursor/include-hidden fields and data/next-cursor response exist | Later full-profile preparation; support and unpaged result still unobserved |
| `config/read` | Cwd/include-layers fields; config/origins required | Later preparation; raw contents are outside this startup diagnostic |
| `configRequirements/read` | Optional requirements response exists | Later preparation |
| `skills/list` | Cwds/force-reload fields; data response exists | Later preparation; installed skills still need actual discovery |
| `mcpServerStatus/list` | Cursor/detail fields and data/next-cursor response exist | Later preparation; disabled status and empty tools still require observation |

The exact schemas are in the [versioned protocol](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/app-server-protocol/schema/json). Matching field names do not prove handler side effects, runtime delivery, pagination behavior, or the installed profile. The existing collector rejects unsolicited messages and pagination; those remain possible outcomes rather than reasons to retry.

## Startup observations and causal limits

Alias setup creates directories, changes modes, creates a lock, and links helpers. Its failure is caught and reported as a warning. That warning does not identify the later fatal operation. The selected source retains this behavior: [warning handling](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/arg0/src/lib.rs#L149-L164) and [alias operations](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/arg0/src/lib.rs#L330-L381).

Configuration, authentication initialization, and environment-manager preparation precede SQLite and can propagate errors. SQLite initialization can write or recover state. The normal structured logger is installed after those stages, so enabling logging alone is not a demonstrated early-failure diagnostic. An installation-identity step later opens its file for reading **and writing**, even if an identity already exists. See [startup ordering](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/app-server/src/lib.rs#L531-L788) and [installation identity](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/core/src/installation_id.rs#L19-L63).

These are candidate failure stages, not a diagnosis of the retained error. The startup filesystem requirements are not exhausted by the inspected subset. The diagnostic keeps the current permission boundary and records actual operations; it does not infer a writable-home fix from the alias warning.

`codex doctor` is not selected. Its source says it runs the full diagnostic set, including authentication, network, MCP, state, and thread inventory checks. That is broader than this startup question. See [doctor scope](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/cli/src/doctor.rs#L153-L182) and [check dispatch](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/cli/src/doctor.rs#L352-L430).

## Concrete proposed invocation

Use one direct start of the bound 0.163.0 executable, with the collector's source-derived argument vector and a newly copied startup fixture cwd. The private plan binds the exact vector, executable, configuration/instruction identities, omission overlay, PATH identity, and copied seed/project evidence. The copied fixture preserves the seed and omission overlay but has no Git baseline; it is not the later representative authoring repository. Original failed-attempt files stay untouched. Do not run the ordinary `prepare --native` command as a shortcut: it creates a project and Git baseline and later runs `--version`, which are distinct operations.

Preserve the current inherited filesystem permission boundary. Do not grant additional writable paths, create a substitute Codex home, change account, invoke the secret provider, or change live settings. Do not override `HOME` or `CODEX_HOME`. The app-server's own environment is inherited by the existing transport; its `shell_environment_policy` applies to later shell tools and is not server-environment isolation.

Send exactly:

```json
{"id":1,"method":"initialize","params":{"clientInfo":{"name":"compatibility-native-preparation","version":"2"},"capabilities":{"experimentalApi":true}}}
```

Validate the four required response fields against the pinned schema and expected Linux/home/runtime identity. Then stop the process. No `initialized` notification or second request is sent in this reduced diagnostic. No model-list, configuration, skill, connector, thread, turn, login, or permission-response operation follows. An unsolicited message, RPC error, unknown response, premature EOF, or bound violation is retained as an incomplete outcome and ends the attempt.

The diagnostic observes only the launched process and its traced descendants, from launch. Its explicit syscall list covers path opens/creation/renames/removal/linking/stat/access/readlink/chdir; descriptor close/dup/locks/truncation/mode/synchronization; and process lifecycle. The private plan enumerates names. No broad syscall class, data-buffer read/write, environment dump, exec argument dump, network payload, or stack dump is requested. Both successful and failed selected operations are needed to reconstruct paths and distinguish tolerated failures from termination. No unrelated process is attached.

Retain selected operation names, bounded path or descriptor metadata, PID/TID, timestamps, flags, return value, and errno. Preserve only the initialize metadata projection and approved diagnostic categories from stdout/stderr. Unknown strings are omitted. The collector must not spool raw configuration or arbitrary output before projection. This is a required implementation behavior, not a privacy guarantee established by this document.

## Bounds, closure, and interpretation

| Item | Proposed bound |
| --- | --- |
| Runtime starts | One, no retries or substitute |
| Startup and response window | 30 seconds |
| Pipe input | 2 MiB combined stdout/stderr; 4 KiB reads; 256 KiB per protocol message |
| Trace | 16,384 records; 4 MiB retained; 4 KiB per record |
| Control/projection records | 256 KiB |
| Observed identities | 32 processes and 256 total process/thread identities |
| Complete local envelope | 4 GiB, subject to fresh admission |
| Shutdown | TERM, at most 5 seconds; KILL if needed, at most 5 seconds for reap/drain/terminal record |
| Total launch-to-terminal | 40 seconds |

Exhaustion stops collection and preserves an explicitly incomplete prefix. The controller must enforce elapsed-time limits during callbacks and shutdown drain, retain direct-child/tracer exits, and reconcile every observed descendant. Unknown closure remains unknown and prevents another invocation; process-group signaling alone is not evidence of complete closure. Existing adopted accounting equipment is reused, not redesigned here.

A successful initialize response establishes startup for this selected runtime/profile, not full profile qualification. An operation/path failure establishes what failed; fatal attribution additionally requires matching source propagation or an explicit diagnostic. The last `EROFS` alone is insufficient. A new runtime's result does not conclusively explain the historical failure. Every outcome leaves the prior attempts intact.

Record preparation and source inspection, runtime/tracer and controller time, read/retained bytes, failed attempts, operator effort if supplied, and unknown costs. No inference is requested; any unexpected provider activity is recorded as a deviation, not silently assigned zero cost.

## Implementation and acceptance join

The trace backend is not available on the current PATH; the package manager reports no installed `strace`. No installation was attempted. Before this proposal can become an execution contract:

1. Select and pin a trace backend through its supported installation route; verify the exact trace options and supported syscalls. No fallback after a failed invocation.
2. Implement the bounded startup-only collector and its projection/closure behavior. Qualify it locally against synthetic child/protocol/trace inputs at agreed CLI/evidence-package boundaries. Existing full-profile transport is not qualified for this narrower retention contract.
3. Reconcile the current profile, exact command, source/schema identities, observed writable boundary, and adopted accounting binding. Any changed protection boundary receives its applicable specialist review.
4. Independently review the final runnable bytes and evidence, then request separate acceptance for the one metadata invocation. A native author episode remains a later acceptance.

Backend/interface preparation and synthetic collector preparation can run independently after their implementation scope is agreed. Join their exact revisions before end-to-end local qualification and review. The System One coordinator owns the join. Neither lane restarts summary-workload recruitment or waits on image-model experiments.
