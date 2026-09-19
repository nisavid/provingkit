# Codex status observation adapter

`scripts/codex_status.py` turns the engine's `observation_requests` into typed
observations by running one fixed, status-only Codex app-server subprocess per
bound route. Standard library only; JSON in, JSON out; no registry- or
config-supplied command, method, argument, endpoint, or shell string.

## Commands

```sh
python3 scripts/codex_status.py describe --binding "$BINDING"
python3 scripts/codex_status.py observe --binding "$BINDING" [--binding "$OTHER"] \
  --requests plan.json [--task-states task-states.json] [--output input.json] [--report report.json] \
  [--now <ISO 8601 with offset>] [--timeout-seconds 30]
```

`describe` prints the safe labels, bucket and model labels, and the effective
`policy_revision` to register gates with. It touches nothing but the config.
`observe` prints a report and, with `--output`, writes `cycle_input` as a
file that `aeon_bell.py cycle --input` accepts unchanged; with `--report`
it also writes the printed report itself (the same JSON as stdout). Both
files are created with mode `0600` (an existing wider file is tightened)
because they carry task ids and observation values. `--requests` is the
engine's cycle output, the engine-directed tick's `plan.json`, or a bare
list of `{gate_key, gate}` objects. `--task-states` is passed through into
`cycle_input.task_states`; the directed tick never passes it. Usage,
config, or input failures print one fixed, value-free line
`codex status: <code>: <message>` and exit 2; the directed tick's monitor
submits that line verbatim, and the engine accepts it up to 498 characters
(its longest line today, the invalid-binding field-set error, is 232) and
relays it untruncated in one diagnostics line. Per-gate holds and transport
failures are reported in the JSON and exit 0.

The directed tick issues this command with exactly these arguments: every
`--binding` it was started with, and `--requests`, `--output`, and
`--report` inside the engine's own `<store>/ticks/<tick_id>/` directory
(`--now` only in supplied time mode). The monitor runs the argv as printed
and submits only the exit code. The engine gives each issued observation a
matched `input-<execution_id>.json` and `report-<execution_id>.json` pair and
reads only the pair bound in that action. A generation takeover keeps the
same `plan.json` but issues a new pair, so a superseded process cannot supply
either artifact consumed by the active continuation.

Output files are written one after the other, `--output` first and then
`--report`, before anything is printed, and there is no transaction across
them or with the process exit. A write that fails is `output-io`, exit 2,
with nothing printed, and a file written earlier in the same run remains as
it was written; an interrupted write can leave a partial file. On exit 2
the engine reads neither file, and on exit 0 it refuses any missing,
unreadable, non-JSON, wrong-shaped, or partially written file in the bound
pair as a failed query with nothing applied. Complete files from a different
execution are outside that pair, so neither leftovers nor overlapping stale
writes are taken for the active observation.

## Binding config

An owner-approved private JSON file, mode `0600`, prepared under the current
routing policy. Exactly these fields, plus optional `expected_account_email`:

```json
{
  "format": "praxis-aeon-bell-codex-binding",
  "version": 1,
  "account": "acct-label",
  "route": "route-label",
  "policy_revision": "policy-2026-09",
  "codex_home": "/absolute/path/to/the/bound/codex/home",
  "expected_account_id": "the exact authenticated account id",
  "quota": {
    "weekly": {
      "limit_id": "exact-limit-id",
      "windows": [
        {"window": "primary", "duration_minutes": 300},
        {"window": "secondary", "duration_minutes": 10080}
      ]
    }
  },
  "models": {
    "daybreak": {"model": "exact-model-slug", "quota": "weekly"}
  }
}
```

- `account`, `route`, and `policy_revision` are the safe labels that appear in
  gates. `codex_home` and `expected_account_id` are private and never printed.
- Identity is bound explicitly; the adapter never infers an account from a
  directory name. A config without `expected_account_id` is rejected.
- Each quota bucket names one exact limit id and every window it requires,
  optionally pinned to a window duration. Each model label names the exact
  slug expected in the live catalog and the bucket its capacity depends on.
- The effective `policy_revision` is `<policy_revision>+<16 hex>`, the hex
  being an opaque digest of the whole config. Any change to the home, account,
  limits, windows, or models changes it; gates registered under the old value
  are `held`, so the owner re-registers or updates them. The revised gate is
  looked up under its new key: a fresh observation already stored there (one
  earned by a gate updated earlier to the same revision) is reused, and a key
  with none is queried; the old key's entry stays in the store, serves only
  registrations that still carry it, and is never borrowed or deleted. Never
  hand-write the suffix.
- The config carries the policy revision label only, never a policy copy.
- Several configs may be passed to one `observe`; their label pairs must be
  distinct. A request is handled by the first config whose labels match.

## Fixed protocol

Per binding with at least one observable gate, and only then:

1. Read `tokens.account_id` from `<codex_home>/auth.json`. Missing file or
   field is `held:credentials-missing`; unreadable is
   `held:credentials-unreadable`; a value other than `expected_account_id` is
   `held:account-mismatch`. Nothing else in the file is read or kept.
2. Launch exactly `codex app-server --stdio -c mcp_servers={} -c features.plugins=false -c features.apps=false`
   with `codex` resolved from `PATH`, an empty temporary working directory,
   and an environment of only `PATH, HOME, LANG, LANGUAGE, LC_ALL, LC_CTYPE,
   TERM, TMPDIR, USER, LOGNAME` plus the explicit `CODEX_HOME`. Stderr is
   discarded.
3. Newline-delimited JSON-RPC over stdio, in this order and nothing else:
   `initialize` with `clientInfo{name,version}` and
   `capabilities.experimentalApi: true`; the `initialized` notification;
   `account/read {refreshToken:false}`; when a `daybreak_status` gate is
   requested, `model/list {includeHidden:true, limit:100, cursor:null}`
   following `nextCursor` for at most 10 pages; `account/rateLimits/read {}`.
   Notifications and server-initiated requests are ignored, never answered.
4. Stop the process on every exit path, then remove the temporary directory.
5. Re-read `tokens.account_id`; a change during the run is
   `held:identity-changed`.

Bounds: one process; whole exchange within `--timeout-seconds` (1 to 120,
default 30); at most 500 messages; one message at most 1 MiB; auth metadata
at most 1 MiB. No login, token refresh, session, thread, turn, tool, or
arbitrary RPC request ever. The harmless runnability probe remains a separate
owner operation under Rolecasting policy.

## Identity evidence

The `account/read` result must show an authenticated account
(`held:not-authenticated` otherwise) whose `type` is exactly the string
`chatgpt`; a missing, non-string, or differently cased `type` is
`held:account-type-unsupported`, never assumed. When the server exposes an account id
(`accountId`, `account_id`, or `id`) or, with `expected_account_email`
configured, an email, it must match (`held:account-mismatch`) and the report
says `server_identity: confirmed`. When the server exposes neither, the report
says `server_identity: unavailable`: the evidence is the local metadata under
the exact bound home plus a server-authenticated account, not a
server-confirmed identifier. Do not overstate it. The report carries only
booleans and states about identity, never values.

## Observation semantics

`quota_recovery`: the gate's bucket label resolves to its limit id and required
windows. The bucket is reported only when the limit id is present and every
required window is present, numeric, within 0 to 100, and matches its pinned
duration. `remaining_percent` is the minimum of `100 - usedPercent` across the
required windows, so any exhausted required window yields 0 and the engine
closes the gate as `bucket-exhausted`. `reset_at` is the bucket's expected
opening, taken only from the windows that block it: the latest `resetsAt`
among the exhausted required windows, since every one of them must recover
before the bucket does. A non-exhausted window's reset is not the hint (a
weekly window with capacity left never postpones the reset of an exhausted
5-hour window), a bucket with no exhausted window carries no `reset_at`, and
when any exhausted window advertises no usable reset the field is omitted
rather than borrowed from another window, so the engine plans its 60-minute
unknown default unless the owner forecasts.
Otherwise the binding and the server disagree about what the bucket is, and
that gate alone is `held:limit-window-missing`: an error observation that
backs off, never opens, and stands as a failing marker until the owner fixes
the binding, so a misconfigured bucket never reads like an exhausted one.
Legacy `rateLimits`, credits, and reset times are never capacity.
`expires_at` is omitted so the engine's 15-minute freshness applies
regardless of any advertised reset. `reset_at` is a scheduling hint only: a
closed gate's next query is planned a quarter of the way to the earliest
applicable reset or owner forecast, bounded 15 to 360 minutes (see the
Schedule section of `engine-cli.md`), and an early recovery is admitted only
by an actual open observation.

`daybreak_status`: `exposed_models` is `[<model label>]` when the exact slug
appears in the paged `model/list` data, else `[]`. `capacity` is `available`
when the bound bucket's composite remaining capacity is above 0 and
`exhausted` when it is 0; when that bucket cannot be resolved the gate is
`held:limit-window-missing` the same way. When the bucket is exhausted and
its blocking windows all advertise a usable reset, the observation also
carries the bucket's `reset_at` (the same value a `quota_recovery` bucket
would carry); an available bucket, or one whose opening is unknown, carries
none. The engine uses that hint for its adaptive plan only when exhausted
capacity is what closed the gate: it is a scheduling hint, never capacity,
never evidence that the model will be exposed, and never proof the route is
runnable. Only metadata is read; no model is executed.

## Outcomes and reasons

| Outcome | Cycle observation | Reasons |
| --- | --- | --- |
| `observed` | typed `ok` | `typed-observation` |
| `held` | `error` (backs off, never opens) | `held:gate-key-mismatch`, `held:policy-revision-mismatch`, `held:bucket-unbound`, `held:model-unbound`, `held:limit-window-missing`, `held:credentials-missing`, `held:credentials-unreadable`, `held:account-mismatch`, `held:identity-changed`, `held:not-authenticated`, `held:account-type-unsupported` |
| `error` | `error` (backs off, never opens) | `error:codex-unavailable`, `error:codex-exit`, `error:codex-timeout`, `error:malformed-response`, `error:rpc-error`, `error:model-list-unbounded`, `error:rate-limits-shape` |
| `unhandled` | none | `binding-labels-differ` (no passed binding owns these labels) |

A `held` gate needs the owner: fix the binding, re-register with the current
`describe` revision, or remove the registration. An `error` gate needs
nothing but the shared backoff. Neither is ever open. Identity and transport
outcomes apply to every gate the binding observes in that run;
`held:limit-window-missing` is one gate's outcome, and the binding's other
gates are observed as usual. Both are standing
conditions keyed by gate and reason code: the engine's `notice` reports the
first sight and a changed reason, stays quiet through identical re-results
and advancing backoff, and reports the clearing once. An `unhandled` gate is
a configuration gap: it produces no observation and no backoff, the engine
requests it again at every tick that runs while deferring the next tick to
its liveness bound, and nothing in `attention` names it. (A tick started
with no `--binding` at all never runs this adapter: the engine records that
gap itself as `no-binding`, with the same deferral, and claims no adapter
outcome for it.) `notice`
learns it only from this report passed as `--adapter-report` (the tick's
actual query set), reports it the first time and as cleared once a binding
with those labels is passed or the owner updates, pauses, or removes the
registration, and keeps it, quietly, across ticks that did not query the
gate. See the quiet rules in `native-monitor.md`.

## Redaction

Output never contains credentials, tokens, account ids, emails, the bound
home path, exact model slugs, or any server output. Only labels, booleans,
percentages, reset times, and fixed reason codes appear. Server error text is
never echoed.

## Assumptions to verify against the installed Codex

- The app-server accepts requests without a `jsonrpc` field and answers with
  `{"id", "result"}` or `{"id", "error"}` objects on one line each.
- `account/read` returns `{"account": {...}|null, ...}` with a `type` and
  optionally an identifier or email.
- `account/rateLimits/read` returns `rateLimitsByLimitId` keyed by limit id
  with `primary` and `secondary` objects of `usedPercent`, `resetsAt`
  (Unix seconds or ISO 8601), and `windowDurationMins`.
- `model/list` returns `data[].model` and `nextCursor`.

The tests exercise these shapes through a fake executable only. A live
qualification against an installed Codex is a separate owner step.
