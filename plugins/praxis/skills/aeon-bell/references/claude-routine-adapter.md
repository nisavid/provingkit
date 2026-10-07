# Claude local one-off Routine adapter

`scripts/claude_routine_adapter.js` maps Aeon Bell's `heartbeat_set` action to
the native `RemoteTrigger` read and partial-update operations for one explicit,
existing local one-off Routine. It is a dormant source binding: controlled
tests exercise its behavior, but this reference does not activate a monitor or
establish installed scheduling behavior.

## Supported configuration and input

The resource is one Node-free ECMAScript expression. Evaluate its reviewed
bytes the same way as `scripts/monitor_binding.js`, then configure its only
factory with:

- `remoteTrigger`: an already configured callable that owns native transport
  and authentication;
- `triggerId`: the nonempty, printable ID of the existing one-off Routine that
  hosts this registry's heartbeat.

The factory returns a frozen object containing `heartbeatSet({engine, action})`.
Pass that function to the common native-adapter factory:

```javascript
const bindingFactory = eval(CONFIGURED_MONITOR_BINDING_SOURCE);
const routineFactory = eval(CONFIGURED_CLAUDE_ROUTINE_ADAPTER_SOURCE);

const routineControls = routineFactory.createClaudeRoutineControls({
  remoteTrigger: CONFIGURED_LOCAL_REMOTE_TRIGGER_CALLABLE,
  triggerId: "CONFIGURED_EXISTING_ONE_OFF_ROUTINE_ID",
});

const nativeAdapters = bindingFactory.createNativeAdapters({
  taskRead: CONFIGURED_TASK_READ,
  runArgv: CONFIGURED_ENGINE_RUNNER,
  send: CONFIGURED_CONTINUATION_SEND,
  emit: CONFIGURED_NOTICE_OUTPUT,
  heartbeatSet: routineControls.heartbeatSet,
});
```

The control accepts only an action whose kind is `heartbeat_set`, whose purpose
is `schedule`, whose `arguments.heartbeat` exactly equals `triggerId`, and whose
`arguments.target_at` is a supported RFC 3339 timestamp with an explicit
offset. Supported timestamps have a four-digit nonzero year, a real calendar
date, `T`, seconds, zero to three fractional-second digits, and either `Z` or a
numeric offset no larger than 14 hours. `-00:00`, leap seconds, normalized
calendar overflows, and precision finer than milliseconds are unsupported. The
adapter converts the represented instant to RFC 3339 UTC for `run_once_at`;
the normalized UTC year must remain within `0001`–`9999`.

The engine accepts a finer-precision clock but normalizes only its selected
heartbeat request target at the scheduling boundary, rounding upward to the
next millisecond when needed. The adapter does not silently truncate a target.
Its authoritative `next_run_at` readback remains an observation and retains
the supported represented instant rather than being request-normalized.

## Owner callable contract

`remoteTrigger` receives exactly one of these native request objects:

```javascript
{action: "get", trigger_id: "CONFIGURED_EXISTING_ONE_OFF_ROUTINE_ID"}

{
  action: "update",
  trigger_id: "CONFIGURED_EXISTING_ONE_OFF_ROUTINE_ID",
  body: {run_once_at: "RFC3339_UTC_TIMESTAMP", enabled: true},
}
```

It returns exactly one transport outcome:

```javascript
{kind: "not_started"}
{kind: "unknown"}
{
  kind: "completed",
  status: 200,
  json: "{\"id\":\"...\"}",
  summary: "optional native display text",
}
```

For `completed`, `status` is the integer HTTP status. A successful response
requires `json` to be a string containing one JSON object. The adapter parses
that field once and never infers facts from `summary`. The callable, not this
resource, establishes whether transport positively completed, positively did
not start, or may have started with an unknown result. A thrown exception or
an invalid transport envelope becomes `unknown`; exception content is not
retained. For a valid `not_started` or `unknown` envelope, the adapter returns
a new object containing only `kind`; unrelated or non-serializable fields do
not cross into the common binding.

## Ordered procedure

1. Validate the complete heartbeat action, configured Routine ID, and target
   timestamp. Unsupported input returns a `not_performed` engine failure and
   makes no native request.
2. Call `get` for the configured `trigger_id`. Require a successful HTTP
   response whose JSON object has the same `id`, a genuine supported
   `run_once_at`, and its own `cron_expression` property explicitly set to
   `null` or the empty string. The Routine may be disabled or may already have
   fired.
3. Call `update` once with only `run_once_at` converted to UTC and
   `enabled: true`. Do not copy `session_request`, `job_config`, account data,
   MCP connections, or any other read field into the update.
4. Only after a positively completed successful update response, call `get`
   once more for the same `trigger_id`.
5. Report `applied: true` only when the readback JSON has the same `id`, has
   `enabled` exactly `true`, and carries a genuine supported `next_run_at`.
   Return that server-observed string as `next_run_at`; do not replace it with
   the requested target. The unchanged engine decides whether the observed
   run is applied on target or applied off target.

The adapter returns only the engine result facts: an applied readback with its
observed deadline, a stable generic failure disposition and reason before an
update can have taken effect, or an outer transport outcome. Raw native JSON,
summaries, arbitrary fields, and exception text do not enter binding or engine
state.

## Failure and uncertainty

A preflight rejection, malformed preflight, wrong ID, missing or invalid
one-off discriminator, or active recurrence completes as `not_performed`
without mutation. A positively not-started preflight or update remains
`not_started`. A non-success update HTTP status completes as `failed` and is
not read back.

Once an update may have started, an `unknown` result, a thrown transport error,
or a completed success envelope with missing or malformed JSON remains
`unknown`. The adapter neither retries the update nor performs a later read.
After a positively completed update, every readback that cannot authoritatively
establish an enabled same-ID Routine with a supported `next_run_at` leaves the
whole operation `unknown`. This includes `not_started` or `unknown` transport,
a thrown exception, missing or unsuccessful status, malformed data, a wrong
ID, a disabled Routine, and a missing or invalid deadline. No branch retries a
mutating request.

Retain the exact engine continuation when this uncertainty strands the binding.
A fresh native invocation enters normally; takeover records the interrupted
heartbeat effect in the durable engine registry and completes without another
write to this Routine. Scheduling stays held until that exact old continuation
receives an authoritative late applied result or a definitive result that the
control was not performed. A late `failed` result does not establish the
effective deadline and does not release the hold. Do not substitute a new
`get`, a fresh binding run, or status output for settlement. The retained
effective deadline is the server-observed `next_run_at`, including an
authoritative late readback.

## Completion limits

This partial binding does not create, run, or fire a Routine; read credentials;
choose a model or job; change session, account, MCP, or deployment
configuration; support recurring Routines; provide task continuation controls;
or establish scheduled-cloud execution. It supplies no conditional-write or
server-generation claim. A newer write read back once does not qualify an
older in-flight write, including one whose result is lost. Installed native
ordering, persistence, registry access, complete harness support, and
activation remain separate work. The source hold can reduce availability
indefinitely when no authoritative result arrives; it does not infer
settlement from a later `get` or add a provider control.
