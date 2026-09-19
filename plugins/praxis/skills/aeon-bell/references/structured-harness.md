# Structured harness binding

Use this procedure when a harness can keep serializable structured values
between calls. The binding owns one monitor invocation from `enter` through
`complete`; the actor supplies key names and, when requested, one bounded
semantic classification. The actor never copies an entry reference,
continuation, action argument, native result, or result JSON through text.

`scripts/monitor_binding.js` is one strict ECMAScript expression. Evaluating
it returns a frozen factory with three stable entry points:

- `createStructuredMonitorBinding({state, engineTransport, nativeAdapters,
  displayPolicy})` returns `{advance}`;
- `createExecCommandEngineTransport({execCommand, writeStdin, workdir})`
  turns binding-built argv into one POSIX-quoted command and follows an exact
  running session until it exits;
- `createNativeAdapters(controls)` binds explicit task-read, argv, send,
  output, and heartbeat controls to the generic action kinds.

The helper uses no import, `require`, filesystem, network, timer, Node API, or
hidden harness API. Node is only the repository's pinned conformance runner.

## Load the governed bytes

Configure the installed helper path, its reviewed lowercase SHA-256, a source
slot, an entry slot, and one run slot outside actor-written prose. The same
trusted transport must read and hash the bytes. For a `functions.exec` client,
one setup call can invoke `exec_command` with this fixed reader, verify its
completed zero-exit result, and store the returned source directly:

```javascript
const loaded = await tools.exec_command({
  cmd: "python3 -c 'import hashlib,json,pathlib,sys; b=pathlib.Path(sys.argv[1]).read_bytes(); print(json.dumps({\"sha256\":hashlib.sha256(b).hexdigest(),\"source\":b.decode(\"utf-8\")}))' 'CONFIGURED_INSTALLED_HELPER_PATH'",
  yield_time_ms: 10000,
});
if (loaded.exit_code !== 0 || loaded.session_id !== undefined) throw new Error("binding source read did not complete");
const document = JSON.parse(loaded.output);
if (document.sha256 !== "CONFIGURED_REVIEWED_SHA256") throw new Error("binding source identity mismatch");
store("CONFIGURED_SOURCE_KEY", document.source);
```

The configured path and digest come from the installed candidate, not monitor
output. Do not replace this with a separate hash command, dynamic import,
`require`, or a model comparison of displayed bytes. If the read, UTF-8
decode, JSON parse, or digest comparison fails, stop unsupported before
`monitor enter`.

Store the exact configured entry value separately under the entry key. Each
later `functions.exec` call loads the source, evaluates it in that call's
isolated V8 runtime, loads the run and entry slots through a synchronous state
adapter, and calls the same entry point:

```javascript
const factory = eval(load("CONFIGURED_SOURCE_KEY"));
const state = {get: key => load(key), put: (key, value) => store(key, value)};
const engineTransport = factory.createExecCommandEngineTransport({
  execCommand: input => tools.exec_command(input),
  writeStdin: input => tools.write_stdin(input),
  workdir: "CONFIGURED_AEON_BELL_SKILL_DIRECTORY",
});
const nativeAdapters = factory.createNativeAdapters(CONFIGURED_NATIVE_CONTROLS);
const binding = factory.createStructuredMonitorBinding({state, engineTransport, nativeAdapters});
const result = await binding.advance({
  runKey: "CONFIGURED_RUN_KEY",
  entryKey: "CONFIGURED_ENTRY_KEY",
  now: CONFIGURED_LOGICAL_TIME,
  classification: CONFIGURED_CLASSIFICATION_OR_UNDEFINED,
});
```

`CONFIGURED_NATIVE_CONTROLS` is built once from the harness's actual native
interfaces. `taskRead` receives stored `host`, `task_id`, and `episode`;
`runArgv` receives the stored argv array and cwd; `send` receives stored host, task id, and
message with no model or effort override; `emit` receives the stored text;
`heartbeatSet` receives the complete frozen action and engine envelope. An
absent control leaves that action unsupported. A synthetic application can
supply recording controls with the same shapes. Do not discover a tool by
name or invent arguments inside the binding.

Each control returns a transport object with `kind` equal to `completed`,
`not_started`, or `unknown`. A completed object keeps the unmodified native
value under `actual_result`. A completed task read also supplies an explicit
bounded `summary` using only `task_status`, `episode_context`, and
`episode_matches`; `episode_matches` is true only when the observed task's
latest turn is still the wait for the supplied episode. The binding carries
that exact expected episode from the engine into both `taskRead` and the
classification view. The configured control and actor compare the bounded
real task context cooperatively; they do not infer a native episode field the
task interface did not supply. A completed send uses only `transport_status`
and `evidence_summary`. Values are printable
scalars, each string is at most 512 characters, and the whole summary is at
most 1024 serialized characters. The binding rejects an absent or malformed
classification summary as unresolved rather than opening raw state. Task-read
time and send evidence remain mechanical fields of `actual_result`, never
actor input. A control that ran and authoritatively reports the engine's exact
`{disposition, reason}` failure form returns that object as `actual_result`;
this is distinct from a positively pre-execution `not_started` transport and
from an `unknown` effect.

## Advance and classify

Call `advance` again only for the same native invocation and the same state
slots. The optional `now` is stored on first entry and reused mechanically on
every engine transition. The result is one of:

- `complete`: the original engine invocation completed;
- `stopped`: the engine definitively refused or stopped, or a positively
  not-started transition exhausted the immediate retry bound;
- `needs_classification`: inspect the stored native episode through the
  harness, then return exactly `{decision_id, choice}` using one listed choice;
- `unresolved`: an effect or engine transition may have occurred without an
  authoritative completed response; never retry, reenter, or replace it;
- `unsupported`: a required structured channel or valid stored run is absent.

For `task_read`, choose only the documented Aeon Bell task status while
judging `expected_episode` against `episode_context` and `episode_matches` in
the classification view. The binding accepts `idle` only when the stored
summary has a string `episode_context` and `episode_matches` is exactly true.
False, absent, or uncertain relation evidence requires a truthful non-idle
choice and cannot authorize a send. The adapter supplies `observed_at`. For `send`, choose
`accepted`, `not_sent`, or `unknown`; the adapter derives evidence from the
stored native result. Free-form fields, stale decision ids, and opaque values
are rejected without another native or engine effect. Display is output-only:
it can be truncated or corrupted without changing execution and is never
accepted as run state.

Every action gets a new monotonic binding id within the invocation. The
decision id includes that binding id, so a decision issued for an earlier
task read or send cannot classify a later action of the same kind.

A positively pre-execution `not_started` continue retries the exact stored
continuation and result JSON, for three immediate attempts. Later advances
may repeat only that same stored continue when the bounded attempts were all
positively not started. An exception, incomplete process, invalid or partial
JSON reply, lost polling session, or other ambiguous outcome is `unresolved`.
The binding never calls `enter` again after run-state creation and never
replays a native action after its start became ambiguous.

An `exec_command` result carrying `session_id` is still running. The supplied
transport polls that exact id until an integer exit code appears and appends
every initial, intermediate, and final output chunk in order before parsing
the one engine JSON reply. A changed or lost session id is unknown.

The state slots are per native invocation. `store` and `load` do not promise
that another heartbeat run can recover them. A new invocation uses the
engine's takeover policy; an in-progress invocation that loses this binding
channel stops unresolved.

## Qualification and activation

The binding preserves the engine registry id, invocation id, generation,
action purpose, heartbeat write number, fingerprint, target, and the native
control's observed prior and resulting run. Those are cooperative facts, not
attestation or scheduling authority.

Heartbeat activation requires a separate native qualification on the same
candidate. Start older write A, apply newer-generation write B, then allow A
to finish after B. Run one case that reports A and one where A's result is
never submitted. The native control must reject or serialize A, terminate or
cancel it within a bound, and authoritatively show B as the final target.
Passing generation data to an unconditional setter, engine fencing, a
submitted `applied` result, manual recovery, or green source tests does not
satisfy this gate. Until that proof exists, `heartbeatSet` remains synthetic
or unavailable and the monitor remains unactivated.
