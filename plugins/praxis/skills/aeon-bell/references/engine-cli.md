# Aeon Bell engine contract

Installed reference for `scripts/aeon_bell.py`, the Python standard-library
engine with no runtime dependency outside this skill. It consumes typed JSON
observations and task states, emits structured proposals, directs the
monitor tick one bound action at a time, and never reads credentials, calls
a service, or executes a native task tool. Paths are relative to the skill
directory. The owner's recipe is the "Owner commands" section and the worked
synthetic example at the end; the monitor's procedure is `native-monitor.md`,
and the "Directed tick" section here is its contract.

## Trust boundary

- Registry records carry no executable content. A continuation is bounded
  text (at most 8000 printable characters) that the monitor passes to the
  native send-follow-up tool as a message.
- Owner identity is cooperative local metadata, not authentication. Owner
  checks protect against accidental cross-owner edits, not a hostile
  same-user process.
- The store is one private directory (mode `0700`) holding one JSON state
  document (mode `0600`) and one `flock` file. Every command is one locked,
  atomic transition. Local POSIX filesystem, one trusted user, one machine.
  The document also holds the private notification state (pending notice,
  acknowledged baseline, and per-gate query knowledge) that `inspect` never
  prints.
- Diagnostics name a stable error code and a short message and never echo
  store contents, inputs, or observation values.

## Time

- Every command accepts `--now <ISO 8601 with offset>`; it defaults to the
  current UTC time.
- Observation freshness and task-state freshness are 15 minutes. Registrations
  expire after 24 hours by default and at most 7 days.
- Freshness and polling are distinct. Freshness is the maximum age at which
  an observation may still open a gate, never a minimum polling interval.
  When a gate is next queried is the schedule (see Schedule): from the
  anchor, the `observed_at` of the gate's latest successful observation, a
  closed gate is due after a quarter of the estimated remaining wait (the
  earliest owner forecast or observed reset hint after the anchor), bounded
  15 to 360 minutes, or after 60 minutes with no such estimate; an open gate
  whose targets are not idle is due when its observation can no longer admit
  (15 minutes from the anchor); an owner's explicit interval (1 to 10080
  minutes) overrides both and may be shorter than freshness, in which case
  the gate is requested again while its observation is still fresh. Repeated
  early reads never move a planned query; a gate whose planned query has
  passed is due now and stays due until it is observed again.
- Provider failures back off on one shared per-gate schedule: 15, 30, 60, 120,
  240 minutes, then a 360-minute ceiling. A successful observation clears it.
  The backoff is a separate bound from the adaptive interval: a gate is
  queried at the later of its planned query and its `next_due_at`.
- At most 3 attempts per episode; the third `not_sent` (reported or
  reconciled) leaves the registration `unresolved` with reason `attempt-limit`
  until the owner rearms or removes it.

## Commands

Owner, legacy, low-level tick, and `monitor bind` commands take `--store
<dir>`. Bound `monitor enter` and `monitor status` take an entry reference;
`monitor continue` takes the issued continuation. Commands that evaluate time
accept optional `--now`. Success prints one JSON object to stdout and exits 0.
Failure prints `aeon bell: <code>: <message>` to stderr and exits 2.

| Command | Arguments | Effect |
| --- | --- | --- |
| `register` | `--owner --host --task-id --episode --gate-json --continuation\|--continuation-file [--expires-in-minutes] [--expected-open-at <ISO 8601 with offset\|unknown>] [--poll-interval-minutes <1..10080\|adaptive>]` | Creates a `waiting` registration. One active registration per `(host, task_id)`. The cadence metadata is optional and outside gate identity (see Owner commands). |
| `inspect` | | Lists registrations, observations, retry schedule, unresolved attempts, `attention` entries (everything no tick will move: registrations `reserved`, `unresolved`, or `expired`, plus outstanding attempts whose registration was removed, listed as `detached`; each with `since` and `next_action`), the `schedule`, and limitations. |
| `update` | `--registration-id --owner [--gate-json] [--continuation\|--continuation-file] [--expires-in-minutes] [--expected-open-at] [--poll-interval-minutes]` | Owner edits. While the registration is `reserved`, its gate and continuation are frozen into the pending attempt and the update fails with `invalid-transition`; expiry and cadence metadata are still accepted, since neither reaches the attempt or its message. A changed gate switches the key its observation is looked up under (see Gates): only a fresh observation already stored under the new key is reused; otherwise the gate is queried. Extending expiry returns an `expired` registration to `waiting`. A new forecast must be in the future and before the expiry this command leaves behind; the expiry is never extended to fit it. |
| `pause` / `resume` | `--registration-id --owner` | `waiting` to `paused` and back. |
| `remove` | `--registration-id --owner` | Owner cancellation. The record is retained as `removed` and hidden from the `inspect` registrations list. An attempt already `reserved` or `unknown` for it is not cancelled: it stays in `attention` as `detached` until `report` or `reconcile` closes it. |
| `rearm` | `--registration-id --owner --episode <new> [--expires-in-minutes] [--expected-open-at] [--poll-interval-minutes]` | Starts an explicit new wait episode. The episode identity must be one this registration has never used, including identities superseded before any attempt (`episode-reused` otherwise). An expired registration needs `--expires-in-minutes`, which sets a new expiry from now (`invalid-transition` otherwise); on an unexpired registration the flag renews the expiry explicitly. Any reserved or unknown attempt for the old episode is marked superseded, never retried. A fresh episode clears the stored forecast unless this command supplies one and keeps the explicit interval unless this command changes it. |
| `cycle` | `[--input <json file>]` | One monitor tick; its output ends with the `schedule`. |
| `report` | `--attempt-id --outcome accepted\|not_sent\|unknown [--evidence-json]` | Records the native send result for a reserved attempt. Only the monitor that holds the reservation and observed the send outcome reports; anyone else (a restarted monitor, an owner) reconciles instead. |
| `reconcile` | `--attempt-id --resolution accepted\|not_sent --evidence-json` | Resolves an `unknown` or abandoned `reserved` attempt with explicit target-transcript evidence. |
| `notice` | `[--adapter-report <observe report>]` | Selects what this tick must relay (see Notification state). Writes a pending notice only when `report` is true; a pending notice is returned unchanged until acknowledged. A valid adapter report is always learned into the private per-gate query knowledge, pending notice or not. Prints the `schedule` beside the notice. The directed tick runs this step itself. |
| `acknowledge` | `--notice-id` | Records that the pending notice with exactly this id was relayed, promoting its snapshot to the baseline, and prints the `schedule`. The directed tick runs this step itself after its notice `emit` is submitted. |
| `monitor bind` | `--store [--initialize-registry] [--registry-id] [--binding <path>]... --heartbeat <reference>` | Binds the canonical existing registry and configured native inputs; explicit initialization is the only monitor operation that may create a missing registry. |
| `monitor enter` | `--entry-ref [--now]` | Claims a newer invocation generation and returns one bound action or completion. |
| `monitor continue` | `--continuation --result-json [--now]` | Applies one typed result for the exact active action, or records a still-applicable exact late effect result from a fenced invocation. |
| `monitor status` | `--entry-ref [--now]` | Read-only redacted coordination and schedule state; never returns resumable work. |
| `tick start` | `[--binding <path>]... [--heartbeat <reference>] [--abandon <tick_id>]` | Starts one directed tick and prints its first pending action (see Directed tick). Refuses `tick-in-progress` while another tick runs unless `--abandon` names it. |
| `tick submit` | `--tick-id --action-id (--result-json \| --result-file)` | Applies the typed result of exactly the pending action, runs the internal phases that need no native effect, and prints the next pending action or the completed tick. Every refusal leaves the store unchanged with the same action pending. |
| `tick status` | | Read-only: the running tick (or null), its pending action with restart advice, the last tick summary, and the schedule. |

Owner commands fail with `owner-mismatch` when the owner differs and
`unknown-registration` when the id is missing or removed. `report`,
`reconcile`, `notice`, `acknowledge`, and the `tick` commands are
monitor-side commands with no owner check. Every owner command prints the
registration plus the `schedule` after the change. `cycle`, `report`,
`notice`, and `acknowledge` are the legacy monitor surface: unchanged, still
valid on a store carrying tick state, and outside the directed recipe.

## Owner commands

The owner is the task that must wait, or a task acting for it. It registers
one continuation per host and task and manages that registration; the
monitor observes and dispatches and runs none of these commands.

1. Take the gate labels and `policy_revision` from the binding the monitor
   uses: `python3 scripts/codex_status.py describe --binding "$BINDING"`.
   Never hand-write the revision; a stale one is held, never observed.
2. Register with the task's own host, task id, and a fresh episode:

   ```sh
   python3 scripts/aeon_bell.py register --store "$STORE" \
     --owner "$OWNER" --host "$HOST" --task-id "$TASK_ID" --episode "$EPISODE" \
     --gate-json '{"kind":"quota_recovery","account":"acct-label","route":"route-label","bucket":"weekly","policy_revision":"policy-2026-09+0123456789abcdef"}' \
     --continuation-file continuation.md --expires-in-minutes 1440
   ```

   The continuation says what to resume and expects the woken task to
   revalidate its own episode, quota, and policy before any work; the wake
   message repeats that. Keep it under 8000 characters with no executable
   content. Add `--expected-open-at <ISO 8601 with offset>` when the owner
   knows roughly when the gate should open, and `--poll-interval-minutes <n>`
   only when an explicit operator or applicable policy requirement fixes the
   cadence; the engine applies that number as given and neither invents
   policy nor resolves a conflict between policies. It applies it only while
   a binding the monitor passes owns the gate's labels; in a configuration
   gap the gate waits for the liveness bound instead (see the cadence
   paragraph below).
3. Record the returned `registration_id`; every later owner command needs it
   and the same `--owner`.
4. Read the returned `schedule`. Registration bytes are persisted, but the
   wait is covered only once the monitor's heartbeat will run by
   `schedule.next_check_at`: compare it with the monitor's next native run
   and, under your own native authority, bring a later or suspended run
   forward to it or wake the monitor explicitly. A new registration is due
   now (`gate-due`, delay 0) until its gate is observed. Do the same after
   any `update`, `rearm`, or `resume` that makes the next check earlier.
   This bring-forward is yours even while a monitor tick is running: a
   change that lands during that tick's scheduling step is covered by it
   and by the next tick, not by the tick in flight.

Owner commands, each printing the registration, its `next_action`, and the
registry's `schedule` after the change:

```sh
python3 scripts/aeon_bell.py inspect --store "$STORE"
python3 scripts/aeon_bell.py update  --store "$STORE" --registration-id "$ID" --owner "$OWNER" --gate-json "$GATE"      # switches the lookup key: a fresh observation already under it is reused, else queried; refused while reserved
python3 scripts/aeon_bell.py update  --store "$STORE" --registration-id "$ID" --owner "$OWNER" --expires-in-minutes 2880 # also revives expired
python3 scripts/aeon_bell.py update  --store "$STORE" --registration-id "$ID" --owner "$OWNER" --expected-open-at "$WHEN" [--expires-in-minutes 2880]  # unknown clears; must be future and before the expiry
python3 scripts/aeon_bell.py update  --store "$STORE" --registration-id "$ID" --owner "$OWNER" --poll-interval-minutes 120  # adaptive clears; accepted while reserved
python3 scripts/aeon_bell.py pause   --store "$STORE" --registration-id "$ID" --owner "$OWNER"
python3 scripts/aeon_bell.py resume  --store "$STORE" --registration-id "$ID" --owner "$OWNER"
python3 scripts/aeon_bell.py remove  --store "$STORE" --registration-id "$ID" --owner "$OWNER"
python3 scripts/aeon_bell.py rearm   --store "$STORE" --registration-id "$ID" --owner "$OWNER" --episode "$NEW_EPISODE" [--expires-in-minutes 1440] [--expected-open-at "$WHEN"] [--poll-interval-minutes 120]
```

Cadence metadata. `expected_open_at` is the owner's forecast of when the gate
opens; `poll_interval_minutes` is the effective cadence the authorized caller
already resolved from explicit operator or applicable policy requirements
(1 to 10080 minutes). Both are stored on the registration, outside gate
identity (the gate key and the observation lookup are unchanged) and outside
the frozen attempt payload (no wake message carries them). A record written
before they existed reads as null forecast and adaptive cadence. A new
forecast must lie after now and before the expiry the same command leaves
behind (`invalid-forecast` otherwise, with nothing written); renew the expiry
in the same command to forecast later, since the engine never extends an
expiry implicitly. A stored forecast is allowed to pass: it is judged at the
observation anchor, not at the clock (see Schedule). `unknown` and `adaptive`
clear the fields. `rearm` starts a fresh wait: it clears the forecast unless
the command supplies one and keeps the explicit interval unless the command
changes it. Neither field reaches past a configuration gap: while no binding
passed to the monitor's `observe` owns the gate's labels (the adapter left
it `unhandled`), or no `--binding` was passed to the tick at all (the tick
recorded `no-binding` and issued no query), the gate is still requested at
every tick that runs, but the schedule defers the next check to the
360-minute liveness bound whatever the explicit interval or forecast says,
until a binding answers it. Supplying that binding is a monitor-side change, not an owner command,
and the owner's bring-forward in step 4 does not cover it: the operator who
adds or fixes the binding brings the existing heartbeat forward or runs its
tick explicitly (`native-monitor.md`, Setup); the run already scheduled at
the liveness bound does not notice the new binding on its own.

`rearm` after a completed, unresolved, or abandoned attempt starts a new wait;
the old attempt is superseded, never resent. Every episode identity the
registration ever used is rejected with `episode-reused`, including one that
was superseded before any attempt. An expired registration is rearmed only
with `--expires-in-minutes`, which starts the new wait with a new expiry;
without it the command fails with `invalid-transition`. While a registration
is `reserved`, its gate and continuation belong to the pending attempt: the
wake message was built from them at reservation, so `update` of either fails
with `invalid-transition` until the attempt is reported, reconciled, or
superseded by `rearm`; the expiry and the cadence metadata can still be
changed meanwhile, and such an update alters nothing about the attempt, its
message, or its eventual reported outcome. `remove`
cancels the wait but not an attempt already reserved: that attempt stays in
`attention` as `detached` until the monitor closes it with evidence. Owner
identity is cooperative metadata guarding against accidental cross-owner
edits, not authentication.

`attention` in `inspect` is the owner's view of stuck work too: an
`unresolved` or `expired` registration names its `next_action` (reconcile
with evidence, rearm, renew the expiry, or remove); a `reserved` entry
belongs to the monitor holding it unless that monitor is gone, in which case
the owner reconciles from the target transcript, never by guessing
`not_sent`.

## Gates

A gate is a JSON object with exactly these fields; its gate key is the SHA-256
of the canonical object (sorted keys, compact separators, UTF-8).

- `quota_recovery`: `kind, account, route, bucket, policy_revision`
- `daybreak_status`: `kind, account, route, model, policy_revision`

Changing any field changes the key, and the key is where the engine looks up
the observation it checks the registration against. Only a matching fresh
observation stored under the new key is reused, whether another registration
or this one earlier earned it; a key with no fresh observation is queried.
Observations under other keys, the old one included, stay in the store, serve
only registrations that carry their key, and are never borrowed or deleted.

## Cycle input

`--input` names a JSON object with only these optional keys:

```json
{
  "observations": [
    {"gate_key": "...", "status": "ok", "observed_at": "...", "expires_at": "...",
     "account": "...", "route": "...",
     "buckets": [{"name": "weekly", "remaining_percent": 0, "reset_at": "..."}],
     "credits": {}},
    {"gate_key": "...", "status": "ok", "observed_at": "...",
     "account": "...", "route": "...",
     "exposed_models": ["..."], "capacity": "available|exhausted|unknown",
     "reset_at": "..."},
    {"gate_key": "...", "status": "error", "observed_at": "...", "reason": "..."}
  ],
  "task_states": [
    {"host": "...", "task_id": "...", "status": "idle|running|completed|archived|canceled|human_waiting|unavailable|unknown", "observed_at": "..."}
  ]
}
```

- Each observation must carry exactly the typed field set for its kind
  (`expires_at` and `credits` optional; for `daybreak_status`, `reset_at`
  optional, an ISO 8601 timestamp with offset or null). Any other field
  rejects the whole cycle without echo and stores nothing; a malformed
  `reset_at` is `invalid-time`, named by field only.
- Either list may be empty. An input with an empty `observations` list and
  fresh `task_states` (the monitor's task-state-only input for a tick with
  no query due) ingests nothing and judges the stored observations against
  those task states through the usual checks: a fresh open observation
  proposes an idle target, a stale one skips as `gate-observation-stale`.
  A bare task-state list, or a `cycle` with no `--input`, admits nothing
  (`invalid-input`, or every target `task-unknown`).
- An observation whose gate key no active registration uses any more (the
  owner removed the registration or changed its gate after the plan cycle) is
  skipped, not rejected: it appears in `ingested_observations` with
  `accepted: false` and reason `gate-not-registered`, nothing is stored for
  it, and the rest of the input applies.
- Evidence is ordered per gate key under its current binding, and the
  successful-observation anchor only moves forward. The key's latest
  evidence time is the later of the stored successful observation's
  `observed_at` (when it was made against the same gate) and the retry
  schedule's last failure. An observation, `ok` or `error`, whose
  `observed_at` is earlier than that is superseded: it is skipped with
  `accepted: false` and reason `observation-superseded`, nothing is stored,
  the anchor, the planned query, and any newer failure state are unchanged,
  and a superseded open observation admits nothing. One stamped at exactly
  that time carries no ordering evidence: the stored state is preserved and
  the input is skipped as `observation-not-newer`, so an identical replay is
  a no-op and a contradictory equal-time input never replaces what is
  stored. A newer observation applies as before, and a newer successful one
  still clears the retry schedule. A gate edit moves the registration to
  another key, whose own evidence is compared the same way; observations
  under the old key are neither compared nor touched. Normal ticks stamp
  the tick's clock and are unaffected; the rule bounds the import path and
  replayed input.
- `quota_recovery` is open only when `account` and `route` match the gate and
  the bucket named by the gate reports `remaining_percent > 0`. Reset
  timestamps, credits, missing or nonmatching buckets, and legacy missing quota
  are closed.
- `daybreak_status` is open only when `account` and `route` match, the gate's
  model is in `exposed_models`, and `capacity` is exactly `available`. Its
  optional `reset_at` is the bound bucket's expected opening as the adapter
  observed it: recorded in the evidence, used by the schedule only when the
  gate closed as `capacity-exhausted`, and never a reason to open, to expect
  a missing model, or to treat the route as runnable. An observation written
  before the field existed reads as carrying none.
- An observation without `expires_at` is fresh for 15 minutes from
  `observed_at`. An imported observation with `expires_at` keeps that expiry
  only when it is earlier; a later one is clamped to `observed_at` plus 15
  minutes, so an import may shorten freshness but never extend it. An import
  may already be stale.
- A `status: error` observation newer than the key's latest evidence
  advances the shared retry schedule for its gate key and stores no result;
  an older or equal-time one is skipped by the ordering rule above and
  advances nothing.
- Task states older than 15 minutes, or absent, are unknown.

## Cycle output

```json
{
  "cycle_at": "...",
  "ingested_observations": [{"gate_key": "...", "accepted": true, "result": "open|closed|error|null", "reason": "...", "fresh": true, "expires_at": "..."}],
  "observation_requests": [{"gate_key": "...", "gate": {}, "kind": "...", "task_ids": [], "reason": "unobserved|stale|due", "freshness_minutes": 15, "cadence": "adaptive|explicit", "interval_minutes": 15, "query_due_at": "..."}],
  "wake_proposals": [{
    "attempt_id": "...", "registration_id": "...", "owner": "...", "host": "...", "task_id": "...", "episode": "...",
    "gate_key": "...", "gate": {}, "gate_observation": {"result": "open", "reason": "...", "observed_at": "...", "expires_at": "..."},
    "attempt_status": "reserved",
    "native_steps": [
      {"step": "recheck", "command": ["inspect"], "require": {"registration_id": "...", "status": "reserved", "attempt_id": "...", "episode": "...", "expired": false}, "on_mismatch": "..."},
      {"step": "read", "tool": "task_read", "arguments": {"host": "...", "task_id": "..."}, "require": {"status": "idle", "episode": "..."}, "on_mismatch": "..."},
      {"step": "send", "tool": "send_follow_up", "arguments": {"host": "...", "task_id": "...", "message": "..."}, "model_override": null, "effort_override": null},
      {"step": "report", "command": ["report", "--attempt-id", "...", "--outcome", "accepted|not_sent|unknown"]}
    ],
    "target_revalidation_required": true, "next_action": "...", "limitations": []
  }],
  "skipped": [{"registration_id": "...", "host": "...", "task_id": "...", "episode": "...", "reason": "..."}],
  "unresolved_attempts": [{"attempt_id": "...", "status": "reserved|unknown", "age_minutes": 0, "next_action": "..."}],
  "attention": [{"registration_id": "...", "host": "...", "task_id": "...", "episode": "...", "status": "reserved|unresolved|expired|detached", "unresolved_reason": null, "attempt_id": null, "since": "...", "next_action": "..."}],
  "schedule": {"next_check_at": "...", "delay_minutes": 0, "reason": "...", "gates": [], "registry": {}},
  "limitations": ["..."]
}
```

`attention` (also in `inspect`) is the one list of everything no tick will
move on its own: every `reserved`, `unresolved`, or `expired` registration,
and every `reserved` or `unknown` attempt whose registration the owner
removed (`detached`, with the attempt's `episode` and `attempt_id`). Every
entry of `unresolved_attempts` therefore has an `attention` entry; an empty
`attention` list with nothing `waiting` is the only silent state. `since` is
when the entry entered its state, read from the record of that transition
and never from `updated_at` (owner metadata that any `update` moves): for
`reserved`, the attempt's `planned_at`; for `unresolved`, the `resolved_at`
of the attempt that was reported `unknown` or, for `attempt-limit`, of the
episode's last `not_sent` resolution; for `expired`, the registration's
`expires_at`, identical whether `inspect` sees it before any cycle or after a
cycle has persisted the status; for `detached`, the later of the removal and
the attempt's last transition. An owner `update` (expiry while reserved;
gate, continuation, or expiry while unresolved) therefore leaves `since`
unchanged. An entry whose `since` is unchanged since it
was last relayed is the same stuck work, not news, and stays in the list
until it is closed. A `reserved` or `detached` entry's `next_action` names
both paths: the monitor holding the reservation reports its own send outcome;
anyone without that knowledge reconciles with target-transcript evidence.

The `recheck` step is an `inspect` against the same store: the monitor sends
only when the named registration is still `reserved` under this `attempt_id`
and `episode` and not expired. A mismatch means the owner removed or rearmed
it, or let it expire, since planning; its gate and continuation cannot have
changed, since both are frozen while reserved. The monitor does not send and
reports `not_sent` if the attempt is still reserved (a superseded attempt takes
no report). The `read` step then requires the target idle and still in this
episode. The recheck and the send are separate steps, so an owner remove or
rearm, or an expiry, landing between them is not prevented (see the
limitations).

Cycle order inside one lock: ingest observations, expire registrations, list
due gate requests from the schedule (one per gate key; a key inside its
backoff window is not due), plan wakes, then compute the schedule of the
state the cycle leaves behind. A registration is proposed only when it is
`waiting`, unexpired, its gate observation is fresh and `open` against the
current binding, and the target's fresh task state is `idle`. Every other case
appears in `skipped` with a reason such as `gate-closed`,
`gate-observation-stale`, `gate-unobserved`, `task-running`, `task-unknown`,
`task-state-stale`, `registration-paused`, `registration-reserved`,
`registration-completed`, `registration-unresolved`, or `registration-expired`.

A request appears once per due gate key: `unobserved` (no usable observation:
none stored, or the registration's gate changed), `stale` (freshness passed),
or `due` (still fresh, but an explicit interval asks again anyway). A gate
whose planned query has not arrived is not requested even when its
observation is stale: a stale closed observation waits for its planned
query, and admission simply has nothing fresh to open. A stale open
observation is due and never wakes anything. A key inside its backoff window
is omitted whatever its plan. When a query is not due, the fresh shared
observation is reused as before.

A proposal reserves an attempt and persists it before returning, so a lost
process, an overlapping run, or a restart sees the reservation and does not
propose the same episode again. Reservation also transfers the registration's
gate and continuation to the attempt: the persisted `message_sha256` digests
the wake message built from them, and `update` of either is refused until the
attempt is reported, reconciled, or superseded, so the message the monitor
sends always describes the registry it rechecks. The attempt also records the
gate it was reserved against, beside its gate key, and keeps it for life: the
registration's gate is the owner's current intent and may be edited once the
attempt is settled, while every label derived from the attempt (its events,
the attention entry it defines) reads the attempt's own gate. The message states that the wake authorizes no
work by itself and instructs the target to revalidate its own eligibility and
policy first; for `daybreak_status` that includes the current Rolecasting
policy and any separately required harmless probe. Proposals omit model and
effort overrides so existing tasks keep their models.

## Schedule

`cycle`, `inspect`, `notice`, `acknowledge`, and every owner command print
the same `schedule` object: the next check this registry needs, computed
from durable state alone (observations, registrations, retry schedule, and
the private notification state), never from a remembered tick, so a
restarted monitor or an owner reads the same recommendation from the same
store.

```json
{
  "computed_at": "...", "next_check_at": "...", "delay_minutes": 0,
  "reason": "gate-due|gate-query|backoff|registration-expiry|notice-pending|reservation-unrelayed|configuration-gap|liveness",
  "gates": [{
    "gate_key": "...", "gate": {}, "kind": "...", "registration_ids": [], "task_ids": [],
    "observation": "open|closed|null", "anchor": "...|null", "fresh": true,
    "basis": "unobserved|binding-changed|open|forecast|reset-hint|no-estimate",
    "estimate_at": "...|null", "cadence": "adaptive|explicit", "interval_minutes": 15,
    "query_due_at": "...|null", "backoff_until": "...|null", "configuration_gap": false,
    "check_at": "...|null", "due": false
  }],
  "registry": {"counts": {"waiting": 0, "paused": 0, "reserved": 0, "completed": 0, "unresolved": 0, "expired": 0},
               "attention": 0, "pending_notice": false, "notification_readable": true, "fingerprint": "<sha256>",
               "tick_in_progress": false, "tick_readable": true},
  "bounds": {"adaptive_min_minutes": 15, "adaptive_max_minutes": 360, "adaptive_unknown_minutes": 60, "adaptive_open_minutes": 15, "recovery_minutes": 15, "liveness_minutes": 360}
}
```

Per gate (one entry per gate key that a waiting, unexpired registration
uses):

- The anchor is the `observed_at` of the latest successful observation under
  the key against the current binding. It is monotonic: superseded or
  equal-time input never moves it backward (see Cycle input). With no anchor
  (never observed, or the registration's gate was edited) the gate is due
  now.
- Closed, adaptive: the estimate is the earliest owner forecast on any
  registration of the key, or the observation's reset hint (a
  `quota_recovery` bucket's `reset_at` when the bucket is exhausted, or a
  `daybreak_status` observation's `reset_at` when the gate closed as
  `capacity-exhausted`; a hint on a `model-not-exposed` or
  `capacity-unknown` closure is ignored), that lies
  after the anchor; `interval_minutes` is a quarter of the minutes from the
  anchor to that estimate, floored, bounded 15 to 360; with no estimate after
  the anchor, 60. Applicability is judged at the anchor: an estimate that
  passes on the clock never postpones a check already planned, and the
  60-minute default takes over only after a later observation whose anchor
  lies past every estimate.
- Open, adaptive (the targets were not idle): the observation's freshness
  end, 15 minutes from the anchor or an import's earlier expiry.
- Explicit: each registration with `poll_interval_minutes` demands the
  anchor plus that interval, whatever the estimates say; it may be shorter
  than freshness. Equivalent gates share one query and the earliest demand
  on the key wins (`cadence` says which kind won); every forecast on the key
  feeds the shared estimate.
- `backoff_until` is the retry schedule's `next_due_at` while it is ahead;
  `check_at` is the later of the planned query and the backoff. `due` is
  true when `check_at` has arrived or nothing bounds the gate, and stays true
  on every read until a new observation moves the anchor.
- `configuration_gap` is true when the latest knowledge for the key is
  `unhandled` (query evidence: the adapter answered that no passed binding
  owns the labels) or `no-binding` (configuration knowledge: a directed tick
  requested the gate with no `--binding` passed at all, so no query was
  issued): the gate is still requested at every tick that runs, but it
  cannot pull the next tick earlier than the liveness bound.

Registry level, `next_check_at` is the earliest of: a due gate (now, delay 0,
`gate-due`); each gate's `check_at` (`gate-query`, or `backoff` when the
backoff is the later bound); each waiting registration's `expires_at`
(`registration-expiry`, never rounded later by an adaptive floor); the
recovery bound of 15 minutes from now while a notice is pending
(`notice-pending`) or a reserved attempt's attention marker has not been
acknowledged (`reservation-unrelayed`); the liveness bound of 360 minutes from
now for a due gate in a configuration gap (`configuration-gap`) or a registry
with nothing waiting (`liveness`). `delay_minutes` is nonnegative whole
minutes rounded up. The recovery and liveness bounds are maximum waits from
the read, not anchored deadlines. `gate-due` says only that some gate is due
now, and `gates[].due` names which; the schedule does not record why (never
observed, a query that failed this tick, or an owner change since the plan).
The directed tick records that itself and chooses the heartbeat target from
it (see "Scheduling decision" under Directed tick). `registry.fingerprint`
digests the scheduling inputs (registrations' scheduling fields and
attempts, observation anchors, retry schedule, pending notice id, baseline
sequence): a fresh read whose fingerprint differs from the one a schedule
was applied from means that schedule's inputs are stale. Tick state is not a
fingerprint input. Malformed notification state leaves the registry readable
(`notification_readable` false) and is treated as nothing acknowledged.
`tick_in_progress` is true while a tick record with status `running` is
stored; `tick_readable` is false when the tick key is malformed, which fails
the tick commands with `corrupt-store` and nothing else.

Worked defaults, anchored on an observation at 12:00 that found the gate
closed: an owner forecast of 12:30 plans 12:15; 17:00 plans 13:15; two days
out plans 18:00; no forecast, or one the observation already missed, plans
13:00. Each later successful observation is the next anchor and tightens
toward a future forecast. An explicit 5-minute interval plans 12:05 with
request reason `due`; an explicit 120-minute interval plans 14:00 even beside
a 12:30 forecast, and the stale closed observation waits meanwhile. A
successful early imported open observation still admits eligible work before
a planned check; a forecast or reset timestamp alone never does.

The schedule is advisory: it authorizes no work, admits nothing (admission
still needs a fresh open observation and a fresh idle task state), and is
not an atomic lease on the native heartbeat. `native-monitor.md` says how
the monitor applies it and rechecks its inputs.

## Attempt lifecycle

| Report or reconcile | Attempt status | Registration status |
| --- | --- | --- |
| `report accepted` | `accepted` | `completed`; episode recorded; no wake until `rearm` |
| `report not_sent` | `not_sent` | `waiting` again, or `unresolved` (`attempt-limit`) when this was the third attempt of the episode |
| `report unknown` | `unknown` | `unresolved` (`delivery-unknown`); never retried automatically |
| `reconcile accepted` | `reconciled_accepted` | `completed` |
| `reconcile not_sent` | `reconciled_not_sent` | `waiting` or `unresolved` (`attempt-limit`) on the third attempt |
| `rearm` | `superseded_reserved` / `superseded_unknown` | `waiting` on the new episode; the old identity joins the registration's `episodes` history and can never be reused |

Reporting an attempt twice fails with `attempt-not-reserved`. The
`delivery_claim` in a report result is `accepted_by_native_send_tool`,
`not_sent`, or `unknown_requires_reconciliation`; the engine never claims
delivery. When the owner removed the registration before the report or
reconciliation, the registration stays `removed` whatever the outcome and the
attempt leaves `attention`; removal alone never closes an attempt.

## Notification state

The store, not the monitor's context, records what was already relayed. Two
commands own it; the monitor only prints text and acknowledges.

```sh
python3 scripts/aeon_bell.py notice --store "$STORE" [--adapter-report <observe report>] [--now ...]
python3 scripts/aeon_bell.py acknowledge --store "$STORE" --notice-id "$NOTICE_ID" [--now ...]
```

`--adapter-report` is the JSON that `codex_status.py observe` prints (or
writes with `--report`). Only `gates` is read, each entry exactly
`gate_key, kind, outcome, reason`; anything else fails with
`invalid-adapter-report` and changes nothing. That list is this tick's actual
query set. Omit the flag when `observe` did not run or exited 2: on exit 2
it printed no report, so a redirected file is empty and is refused. The
directed tick passes the report it learned from its own `report.json`
internally and never a report from a failed or unissued query.

`notice` compares three things with the acknowledged baseline and prints one
object:

- **Standing markers** (`markers_now`, `new`, `cleared`). `attention:<registration_id>:<status>:<since>`
  for every `attention` entry; `unhandled:<gate_key>` for a gate that a
  waiting registration uses and the adapter report left `unhandled`;
  `no-binding:<gate_key>` for a gate that a waiting registration uses and a
  directed tick requested with no `--binding` passed at all (configuration
  knowledge the tick learns from its own inputs, never an adapter outcome);
  `failing:<gate_key>:<reason>` for a gate that a waiting registration uses
  and that sits in `retry_schedule` (the reason is the last `held:` or
  `error:` code, so an identical re-result after backoff, an advancing failure
  count, or a moved `next_due_at` is not a change; a different reason is).
  `new` lists markers absent from the baseline. `cleared` lists baseline
  `unhandled`, `no-binding`, and `failing` markers absent now, because those conditions can
  return and must then read as new; an `attention` marker that left is the
  owner's or monitor's own action and drops silently. A gap or failure is
  also cleared when nothing waits on the gate any more (removal, pause,
  update, completion, expiry).
- **Coverage** (`coverage`). An `unhandled` marker is learned only from a
  query; a `no-binding` marker only from a directed tick whose query was not
  issued for `no-binding`, for the gates it requested. The store keeps the
  latest knowledge per gate (the private query knowledge): every valid
  `--adapter-report` updates it for the gates it lists, and a directed tick
  records `no-binding` for its requested gates, under the store lock,
  whether the tick is quiet, presents a new notice, or replays a pending
  one. `coverage.adapter_report` and `coverage.queried` describe the adapter
  report alone: a `no-binding` tick has no report and an empty queried set,
  because nothing was asked. A gate that this tick did not cover (no
  adapter report, backoff, fresh cache) keeps its latest known outcome; when
  that outcome is a gap it is listed under `coverage.retained`. Absence
  of an observation never clears a gap, and a gate never covered is neither a
  gap nor a clear. A valid covered result for the gate (`observed`, `held`,
  or `error`) ends either gap, even when it was learned during a replay
  tick; an `unhandled` answer ends a `no-binding` gap and is itself new. A
  binding passed whose query fails (exit 2, the failure form, or unusable
  files) learns nothing: a `no-binding` gap stays retained, exactly like an
  `unhandled` one, until a query answers the gate.
  Knowledge is dropped for a gate nothing waits on any more (removal, pause,
  update, completion, expiry) when the next fresh notice is computed, which
  is where that gap reads as cleared; a resumed or re-registered gate has no
  marker until it is queried again.
- **Events** (`events`). Every persisted attempt whose status is `accepted`,
  `not_sent`, `unknown`, `reconciled_accepted`, or `reconciled_not_sent` and
  whose exact identity (attempt id plus that status) the baseline has not
  acknowledged, oldest first, with `delivery_claim` and `next_action`. A
  `not_sent` or `reconciled_not_sent` event's `next_action` follows the
  registration's current state (waiting again, removed, rearmed, paused,
  reserved again, completed, unresolved, or expired), not the lifecycle
  table row. Two
  events resolved at the same second are two events. Superseded attempts
  (owner `rearm`) are not events. Events are bounded to the attempts the
  store already persists; there is no separate log.

`report` is true when `new`, `cleared`, or `events` is nonempty. Then `text`
holds the literal lines to relay, `notice_id` a 24-hex id, and the pending
snapshot is written to the store. `text` names gate kind, account and route
labels, registration and attempt ids, statuses, `since`, reason codes, and
next actions, and starts with the snapshot time; it never carries host or
task ids, episodes, continuation text, observation values, or binding
values. The labels on an event, on an attention entry defined by an attempt
(`reserved`, `unresolved`, `detached`), and on a gap or failure marker whose
key is found only through an attempt are the gate that attempt was reserved
against, whatever the owner has since done to the registration's gate; an
`expired` entry and a marker on a gate a waiting registration uses name the
registration's current gate. An attempt written before the engine recorded
the gate on it resolves those labels only from a record that still carries
the same gate key (an identical key is an identical gate); with none, the
labels are `unknown`, never the registration's edited gate. A quiet tick (`report` false) presents nothing and needs no
acknowledgement; quiet refers to the emitted notification, and the tick's
query knowledge is still persisted when it changed.

A pending notice is immutable. Until it is acknowledged, every further
`notice` returns the same `notice_id`, `computed_at`, and `text` with
`replayed: true`, whatever the registry or the clock did meanwhile; only
after `acknowledge` does the next `notice` compare the current state. So a
relay that crashed before acknowledging is relayed again, possibly more than
once (at least once, never dropped), and a change that lands while a notice
is pending, in the registry or in the adapter reports of the replay ticks,
is reported by the first `notice` after acknowledgement.

`acknowledge` binds to the pending id only: it advances the baseline
(`sequence` plus 1, `markers` from the snapshot, the snapshot's event ids
added to the acknowledged set) and clears the pending notice; it never reads
or rewrites the query knowledge, so nothing learned since the snapshot is
consumed by acknowledging it. The id most
recently acknowledged is answered again with `already-acknowledged` and no
change, even while a newer notice is pending; any other id fails with
`unknown-notice` and changes nothing. Acknowledgement records the caller's
assertion that the text was relayed: it proves durable selection, not that a
person received or read anything, and it adds no delivery claim.

The state (baseline, pending notice, and query knowledge) lives under one
private additive store key that `inspect` never prints; the format version
is unchanged. The query knowledge holds gate keys and fixed codes only: the
adapter outcomes and the tick's own `no-binding`. A store written before this key existed reads as an empty baseline:
its first `notice` reports every standing condition and every terminal
attempt it holds once (the bootstrap), and nothing is silently seeded away.
A store written before the query knowledge existed reads its knowledge from
the `unhandled` markers it already holds (the pending snapshot's if one is
pending, else the baseline's), which is what it retained before, and is
rewritten only when that knowledge changes. Malformed notification state,
including malformed query knowledge, fails `notice` and `acknowledge` with
`corrupt-store` and leaves the registry readable and untouched; an attempt
whose recorded gate is malformed or does not match its gate key fails
`notice` the same way. Engine or
adapter exit 2 is not notification state; the monitor reports it directly
that tick.

## Registry-bound monitor entry

The native monitor uses one configured registry entry. Binding is an explicit
setup transition:

```sh
python3 scripts/aeon_bell.py monitor bind --store "$STORE" \
  [--initialize-registry] [--registry-id "$REGISTRY_ID"] \
  [--binding "$BINDING"]... --heartbeat "$HEARTBEAT"
```

Without `--initialize-registry`, an absent `state.json` is
`registry-not-found` and no directory, lock, or state is created. Explicit
initialization creates an empty registry when necessary. The result is
`status: bound`, a 32-hex `registry_id`, `config_revision`, `entry_ref`, and
`store_created`. Reconfiguration supplies the current `--registry-id`, is
refused while an invocation or tick is active, and increments
`config_revision` only when the binding paths or heartbeat change. Binding
paths may be an empty configured list; due gates then retain the existing
quiet `no-binding` knowledge behavior.

Each native run starts and advances only through:

```sh
python3 scripts/aeon_bell.py monitor enter --entry-ref "$ENTRY_REF" [--now "$NOW"]
python3 scripts/aeon_bell.py monitor continue --continuation "$CONTINUATION" \
  --result-json '<result>' [--now "$NOW"]
python3 scripts/aeon_bell.py monitor status --entry-ref "$ENTRY_REF" [--now "$NOW"]
```

These replies are also the unchanged engine seam consumed by
[`structured-harness.md`](structured-harness.md). A supported structured
harness stores the configured entry, each parsed reply, continuation, action,
native result, and one serialized result JSON without routing them through
actor text. Its transport classifies only completed, positively not started,
or unknown process outcomes. That consumer adds no token semantics, restart
policy, native-effect proof, or heartbeat ordering authority; the command
contract in this section remains the source of every accepted field.

`enter` opens the canonical store carried by the reference without creating
it, checks the registry id and configuration revision, claims the next
generation under the store lock, and returns either `action_required` or
`complete`. `action_required` carries `registry_id`, `invocation_id`,
`generation`, one engine-issued `continuation`, and one `action` with its
`kind`, `purpose`, fully bound `arguments`, `require`, `result_shape`, and
`failure_form`. Entry and continuation values are routing and
accidental-misbinding data. They are not secrets, authentication, caller
attestation, or proof that a native effect occurred.

`continue` validates the continuation against the one active invocation and
pending action, applies one typed result, consumes that continuation for
advancement, and returns the next `action_required` or `complete` result.
`invalid-result`, `stale-result`, and `tick-clock` leave the same continuation
active for a corrected retry. Reusing an already advanced continuation is
`stale-result`. A superseded read or observation result is
`stale-invocation: this invocation was superseded; stop`.

Newest entry wins. A takeover with a pending `task_read` or `observe` retains
the current tick and its action, refreshes the action's issue time, and returns
the same safe action through a continuation bound to the new generation. A
pre-send read therefore retains its proposal and reservation and reaches the
existing rechecks normally; an observation retains its engine-owned plan and
artifact directory but receives a fresh `input-<execution_id>.json` and
`report-<execution_id>.json` pair. The active continuation reads only that
pair, so a superseded adapter process may finish without contributing either
artifact to the active result. A takeover retains an interrupted send
reservation without issuing another send, replays durable notice or
diagnostics, and recomputes the heartbeat write from current state. An older actor may submit only the
continuation for the exact interrupted effect it was issued. A
still-applicable result is recorded once and returns `status: stopped`,
`reason: superseded-invocation`, and `late_result: recorded`; later reports
return `already-settled`. No stale result can advance the newer invocation.

`status` never resumes work. It exposes registry and invocation ids,
generation, transition times, phase, pending kind/purpose/time and
interruption class, interrupted-effect counts, a redacted last summary, and
the schedule's timing, cadence, counts, and fingerprint. Its schedule
projection omits gate identity, registration ids, and task ids. It does not
expose an entry reference, continuation, action id,
binding path, heartbeat, target, episode, action arguments, wake message or
digest, notice text, or adapter argv.

A wrong executable path or malformed shell/argv transport fails before this
interface runs and is not an Aeon Bell refusal. A copied registry at another
canonical path, a stale revision, or an altered reference is refused as
`registry-mismatch`; no reference authenticates a cooperative same-user
caller.

## Directed tick

The directed tick is the implementation under the bound monitor entry. Its
low-level commands remain available for compatibility and public tests. Each
`tick start` or `tick submit` runs inside one `transaction(write=True)`:
it validates the durable tick record, applies at most one submitted result,
runs every internal phase that needs no native effect, issues at most one
next action with fully bound arguments, and saves. Every exit 2 raises
before the save, so `state.json` is byte-identical and the same action stays
pending. The monitor performs the pending action with its own native tool
and submits the typed result; the engine binds and orders those results,
applies their consequences, and never verifies that the tool was invoked or
that a result is true.

### Commands

```sh
python3 scripts/aeon_bell.py tick start  --store "$STORE" [--now <ISO 8601 with offset>] [--binding <path>]... [--heartbeat <reference>] [--abandon <tick_id>]
python3 scripts/aeon_bell.py tick submit --store "$STORE" --tick-id <24-hex> --action-id <12-hex> (--result-json '<json>' | --result-file <path>) [--now ...]
python3 scripts/aeon_bell.py tick status --store "$STORE" [--now ...]
```

`tick start`: `--binding` is repeatable; each path is made absolute against
the command's working directory and recorded as a string; the engine never
reads it. `--heartbeat` is the opaque reference of the one existing
heartbeat as the harness's control names it (validated as printable text of
at most 256 characters, `invalid-identity` otherwise), stored verbatim and
echoed on every `heartbeat_set`; without it no heartbeat write is issued.
`--abandon` must name the running tick: any other value while a tick runs
is `tick-in-progress`, and naming a tick that is not running is
`tick-not-running`. `--now` fixes the tick to supplied time mode; its
absence fixes clock mode. In one transition the command validates the tick
key, abandons the running tick when told to (see Restart), sweeps every
other `ticks/<24-hex>/` directory under the store, expires registrations,
snapshots the ids of the waiting unexpired registrations in sequence order,
creates the record in phase `task_states`, and issues the first action.
Exit 2 codes: `tick-in-progress`, `tick-not-running`, `corrupt-store`,
`invalid-identity`, `invalid-time`, `invalid-store`, `store-io`.

`tick submit`, in this order, each exit 2 with the store unchanged:
`--result-file` unreadable or not UTF-8 JSON, or `--result-json` not JSON,
is `invalid-result`; a malformed tick key is `corrupt-store`; a tick id that
is neither the current nor the last tick is `unknown-tick`; the last tick's
id is `tick-not-running`; a time mode mismatch, or a supplied `--now`
earlier than the tick's last transition time, is `tick-clock`; an action id
other than the single pending action (already dispositioned, unknown, or
future alike) is `action-not-pending`; a result that is not exactly the
action's result shape or the failure form is `invalid-result`; a `task_read`
whose `observed_at` lies outside `[issued_at - 60s, now + 60s]` is
`stale-result`. A `corrupt-store` raised by an internal phase (malformed
notification state, a malformed attempt gate snapshot) also leaves the store
unchanged with the same action pending; the operator repairs the store as
for legacy `notice` and resubmits or abandons. Then the result is recorded
with its disposition and `submitted_at`, its consequence is applied, the
phases advance, and the next action is issued or the tick completes.

`tick status` is read-only (`transaction(write=False)`) and prints the same
view with `pending_action` null when no tick is running. It fails with
`corrupt-store` when the tick key is malformed; the registry itself stays
inspectable through `inspect`.

### TickView

Every tick command prints one object:

- `tick`: the record (null from `tick status` when nothing runs): `tick_id`,
  `status` (`running|complete|abandoned`), `started_at`, `finished_at`,
  `last_now`, `time_mode`, `phase`
  (`task_states|observe|dispatch|notice|schedule|diagnostics|done`),
  `binding_paths`, `heartbeat`, `registration_order`, `task_states`,
  `requested_gate_keys`, `observe` (`issued`, `not_issued_reason`
  `no-request|no-binding|artifact-io|null`, `exit_code`, `failure_line`,
  `artifacts_code`
  `invalid-adapter-report|invalid-observation|invalid-input|artifact-io|null`,
  `answered_gate_keys`, `unanswered_gate_keys`, `adapter_report_learned`,
  `adapter_report`: gate key to outcome, or null), `proposals` (attempt,
  registration, episode, and message digest; never the message), `dispatch`
  (`skipped` with `registration_id` and the existing skip reason codes,
  `attempts` with `stage` `recheck|pre-send|send` and `result`
  `accepted|not_sent|unknown|superseded`, and the cursor), `notice`
  (`notice_id`, `replayed`, `emitted`, `acknowledged`, `consequence`),
  `heartbeat_writes` (at most two: `write_number`, `target_at`,
  `delay_minutes`, `rule`, `fingerprint`, `result`, `next_run_at`,
  `reason`, `basis`), `registry_changed_after_last_write`, `diagnostics`
  (the prose lines emitted at the end of the tick, in order), and
  `actions` (ordered; each `action_id`, `kind`, `purpose`, `issued_at`,
  `submitted_at`, `disposition`
  `pending|performed|not_performed|failed|unavailable`, `reason`,
  `consequence`, `recorded`, `restart`; never the arguments).
- `pending_action`: `action_id`, `kind`, `purpose`, `arguments` (below),
  `require` (the pre-send expectation `{"status": "idle", "episode": ...}`,
  else null), `result_shape`, `failure_form`, `restart`
  (`resumable|abandon-only`), and a fixed `note`; null when nothing is
  pending.
- `last_result`: `action_id`, `disposition`, `consequence` of the action
  just applied (or, from `tick status`, the last dispositioned action).
- `outcome_when_complete`, only on the transition that completes the tick:
  `wakes` (`attempt_id`, `registration_id`, `result`), `notice`
  (`notice_id`, `acknowledged`, `replayed`), `heartbeat` (`issued`, `rule`,
  `target_at`, `delay_minutes`, `writes`, `result`
  `applied|applied-off-target|unavailable|failed|not_performed|not-issued`,
  `reason`, `fingerprint_applied_from`, `registry_changed_after_last_write`),
  and `printed_anything`.
- `last`: the previous tick's summary (`tick_id`, `status`
  `complete|abandoned`, `started_at`, `finished_at`, `abandoned_pending`
  with `action_id`, `kind`, `purpose`, `attempt_id`, `notice_id` or null,
  `actions` as `kind`, `purpose`, `disposition`, and
  `diagnostics_unemitted`).
- `schedule`: the existing schedule object recomputed from durable state at
  this transition.
- `limitations`: the native limitations, the notification limitation, and
  `results_are_caller_assertions`.

The view never carries observation values, continuation text, binding
contents, or wake message text outside the pending `send` action's own
`arguments`; diagnostics carry only engine codes, the adapter's own
redacted error line, ids, times, and counts.

### Actions and arguments

| Kind | Purpose | Arguments | Restart |
| --- | --- | --- | --- |
| `task_read` | `task-state` (one per snapshotted registration, in sequence order) or `pre-send` | `host`, `task_id`, `registration_id`, `episode`, `attempt_id` (pre-send only), `require` (pre-send only) | `resumable` |
| `observe` | `query` | `argv`: `python3`, the absolute path of `codex_status.py` beside the engine, `observe`, `--binding <path>` per recorded binding, `--requests <store>/ticks/<tick_id>/plan.json`, `--output .../input-<execution_id>.json`, `--report .../report-<execution_id>.json`, and `--now <issue time>` in supplied mode only; `cwd` null. The 24-hex execution id is shared by that output/report pair and replaced whenever takeover reissues the observation. `--task-states` is never passed. | `resumable` |
| `send` | `wake` | `tool: send_follow_up`, `host`, `task_id`, `message` (the exact wake message built at reservation), `message_sha256`, `model_override: null`, `effort_override: null`, `attempt_id`, `registration_id`, `episode` | `abandon-only` |
| `emit` | `notice` or `diagnostics` | `channel`, `text` (exact), `notice_id`, `replayed` | `abandon-only` |
| `heartbeat_set` | `schedule` | `heartbeat` (the reference from `--heartbeat`), `target_at`, `delay_minutes`, `rule`, `write_number` (1 or 2), `fingerprint` (the schedule fingerprint the target was chosen from), `basis` | `abandon-only` |

### Result shapes and consequences

Exact key sets; any missing or extra key, wrong type, or value outside its
enumeration is `invalid-result`. Free text is printable and at most 256
characters. The failure form
`{"disposition": "not_performed|failed|unavailable", "reason": "<text>"}`
is accepted for every kind: `not_performed` means the tool or argv was not
invoked; `failed` means it was invoked with no interpretable answer (for a
send the engine records `unknown`); `unavailable` means the tool or control
does not exist for this target or heartbeat.

| Kind | Result | Consequence |
| --- | --- | --- |
| `task_read` (task-state) | `{"status": <task status>, "observed_at": <ISO with offset>}` | `task-state-recorded`; the failure form is `no-task-state` (the result cycle skips the registration as `task-unknown`) and one diagnostics line `task-read-failed`. |
| `task_read` (pre-send) | same | idle, fresh, and still reserved: the `send` is issued; otherwise the attempt is reported `not_sent` with evidence `{"read": <status or disposition>, "reason": <null, the failure reason, task-state-stale, or gate-observation-stale>}` (`attempt-not-sent`, or `attempt-superseded` when an owner or legacy actor settled it meanwhile). |
| `observe` | `{"exit_code": 0}` or `{"exit_code": 2, "stderr_line": "codex status: <code>: <message>"}` (the adapter's verbatim line: printable, at most 498 characters, which is the 512-character diagnostics line bound less the `step observe: ` relay prefix, so it is never truncated on relay; longer is `invalid-result`) | exit 0: the `report-<execution_id>.json` and `input-<execution_id>.json` pair bound in the active action is read, the report validated, the observations ingested, `observation-ingested`; another execution's pair is never consulted. Any unreadable, non-JSON, wrong-shaped, or partially written bound file, or an invalid observation, rolls the ingestion back and is `query-failed` with `artifacts_code`. Exit 2 and the failure form are `query-failed` with the line kept verbatim in `failure_line` and one diagnostics line; the files are not read. |
| `send` | `{"outcome": "accepted\|not_sent\|unknown", "evidence": {optional flat scalar object}}` | `attempt-accepted`, `attempt-not-sent`, `attempt-unknown` through the same report path as legacy `report`; `not_performed` and `unavailable` are `not_sent` with `{"disposition", "reason"}` as evidence, `failed` is `unknown`; an attempt an owner rearmed or a legacy `report` settled meanwhile is `attempt-superseded`, never a tick failure. Results carry no time and are recorded whenever submitted. |
| `emit` (notice) | `{"emitted": true}` | the notice is acknowledged (`notice-acknowledged`; `notice-acknowledged-elsewhere` when a legacy `acknowledge` got there first); the failure form leaves it pending (`notice-still-pending`, one diagnostics line `notice-unrelayed`) for the next tick to replay. |
| `emit` (diagnostics) | `{"emitted": true}` | `diagnostics-emitted`; the failure form is `diagnostics-unemitted` and the lines are kept on the tick summary. Either completes the tick. |
| `heartbeat_set` | `{"applied": true, "next_run_at": <ISO with offset>, "previous_next_run_at": <optional>}` | `heartbeat-applied`; a run more than 60 seconds from `target_at` is `heartbeat-applied-off-target` with one diagnostics line naming the minute difference; the failure form is `heartbeat-control-failed` with one diagnostics line, no second write, no fallback cadence. |

Consequence codes: `task-state-recorded`, `no-task-state`,
`observation-ingested`, `query-failed`, `attempt-accepted`,
`attempt-not-sent`, `attempt-unknown`, `attempt-superseded`,
`notice-acknowledged`, `notice-still-pending`,
`notice-acknowledged-elsewhere`, `diagnostics-emitted`,
`diagnostics-unemitted`, `heartbeat-applied`,
`heartbeat-applied-off-target`, `heartbeat-control-failed`.

### Phases

`task_states`: one `task_read` per snapshotted registration. `observe`: the
plan cycle (`_expire_registrations`, one request per due gate key) records
`requested_gate_keys`; no request is `no-request`, a request with no
binding path is `no-binding` (no diagnostics line: the notice step learns
it as the `no-binding` standing condition for every requested gate, relayed
once and quiet while unchanged, and the schedule treats those gates as a
configuration gap), a directory or
`plan.json` that cannot be written is `artifact-io` with one line; otherwise
the query is issued. `dispatch`: the result cycle (expire, plan wakes,
reserve) runs whether or not a query was issued, so no query due never
means no processing; then, per reservation in order: the recheck at issue
(attempt still `reserved`, registration `reserved` under this attempt and
episode, unexpired; a mismatch on a still-reserved attempt is reported
`not_sent` with `{"recheck": <reason>}`, on a settled attempt it is
`superseded`, and no action is issued), the pre-send read, and the send.
`notice`: the notice selection with the learned adapter report (or none);
`report` false moves on, else the `emit` is issued. `schedule`: with no
heartbeat reference, one diagnostics line `heartbeat-unconfigured` naming
the unapplied next check; else the scheduling decision and `heartbeat_set`
write 1; after an applied write the schedule fingerprint is recomputed
once: unchanged ends scheduling, changed after write 1 chooses again and
issues write 2, changed after write 2 adds `schedule-raced` and sets
`registry_changed_after_last_write`. `diagnostics`: a nonempty list is one
`emit`. `done`: the record becomes the `last` summary, the save runs, and
the artifact directory is removed best-effort afterwards.

A tick reaches `complete` only when every issued action has a non-pending
disposition; the record never holds two pending actions; a missing result
never counts as a performed step.

### Pre-send freshness

The existing admission rules hold at the send, not only at the plan: a send
is issued only when the pre-send read is idle, `observed_at` plus 15 minutes
is still ahead of the submit time (the task-state freshness rule), and the
observation the attempt was reserved against is still fresh (its stored
`expires_at` while the store still holds that observation, never later than
15 minutes from its timestamp). A read that aged past the window before it
was submitted is still recorded (`stale-result` refuses only a read stamped
before its action or in the future), and the attempt is reported `not_sent`
with reason `task-state-stale` or `gate-observation-stale`, so the
registration waits again under the existing attempt count and the next tick
re-observes. A send result is recorded however late it arrives: a native
send that already happened is never refused.

### Durable state, validation, and repair

One additive private key `tick` beside `notification` in the same document,
`{"current": <record or null>, "last": <summary or null>}`; the format
version is unchanged, `inspect` never prints it, and legacy commands ignore
it except for the two additive schedule fields. Tick commands validate it
strictly and fail closed with `corrupt-store` on any unsupported shape: key
sets other than the documented fields, ids that are not 12-hex or 24-hex,
unparseable times, a phase, status, kind, purpose, disposition, or
consequence outside its enumeration, more than one pending action or a
pending action that is not last, a proposal whose attempt is absent from
`attempts` or whose stored message digest differs from its own or the
attempt's `message_sha256`, a snapshotted registration id the store does not
hold, or diagnostics beyond the bound (32 lines of at most 512 characters,
plus one counting line into which further lines collapse). Repair is the
operator's: delete the key from `state.json` under the store's own lock
discipline, as for malformed notification state. Reservations and notices
live outside the key and are unaffected; the orphaned artifact directory is
swept by the next `tick start`. There is no id-less discard flag.

Actions are issued only from validated records: a `send` only while the
attempt is still reserved and the stored message digest equals the
attempt's; a notice `emit` only for the notice the store holds pending; a
`heartbeat_set` only with a heartbeat reference.

### Artifact directory

`<store>/ticks/<tick_id>/` (directory `0700`, files `0600`) holds
`plan.json` (the engine's `{"observation_requests": [...]}`) and one or more
adapter result pairs named `input-<execution_id>.json` and
`report-<execution_id>.json`. One 24-hex execution id binds each pair; a
takeover keeps `plan.json` and binds the reissued action to a fresh pair. The
directory is created and `plan.json` written inside the transition that issues
`observe`, before the save, and kept until the tick ends so a lost observe
submit can be re-performed with the same plan and isolated result paths. It is
removed best-effort after the save
that completes or abandons the tick, and every `tick start` sweeps every
other `ticks/<24-hex>/` directory. The removal rule refuses a symlink or a
non-directory, unlinks only regular `plan.json`, legacy `input.json` and
`report.json`, and execution-named input/report files, then
removes the directory; any other entry or filesystem error leaves the
directory in place and adds `artifact-io: ticks/<id> could not be removed`
to the current tick's diagnostics (or, at completion, to
`last.diagnostics_unemitted` in the printed view). Nothing outside
`<store>/ticks/` is ever removed. Filesystem artifacts are outside the
atomicity of the JSON document: a `plan.json` written in a transition whose
save failed may remain and is overwritten on retry or swept later.

### Time rules

The time mode is fixed at `tick start`. In supplied mode every submit must
pass `--now`, never earlier than the tick's last transition time (equal is
allowed, so a harness may pass one logical time for the whole tick); the
recipe gives `observed_at` that same logical time. In clock mode no submit
passes `--now`; a wall clock that regressed is clamped to the tick's last
time with one diagnostics line `clock-regressed` per tick. Every action's
`issued_at` is the transition time that issued it. `send`, `emit`, and
`heartbeat_set` results carry no time field and are recorded at any later
time.

### Scheduling decision

At each heartbeat write the engine recomputes the schedule and classifies
every due gate (a gate in a configuration gap, `unhandled` or `no-binding`,
is already deferred to the liveness bound by the schedule and counts as
none of these; a nearer expiry, another gate's planned check, or a pending
notice or unrelayed reservation still bounds it):

- fresh owner work: due and not in this tick's `requested_gate_keys` (a
  registration, gate edit, resume, or advanced deadline that landed during
  the tick);
- answered-still-due: requested and answered this tick, due again on its
  own account (an explicit interval already elapsed, or evidence already
  stale);
- unanswered: requested, no accepted ingestion (the query was not issued
  for `artifact-io`, exited 2, was not performed, its files were unusable,
  or the adapter listed the gate without an observation); a query not
  issued for `no-binding` is a configuration gap, not an unanswered gate.

Rules in order: (1) any fresh-owner-work gate: rule `fresh-owner-work`,
target now, delay 0. (2) Any answered-still-due gate: rule
`schedule-as-printed`, target `schedule.next_check_at` (`gate-due`, now):
an independently due gate keeps its own deadline, and any unanswered gate
is retried at that same run, never earlier on its own account and never
later. (3) Any unanswered gate: rule `failed-observation-recovery`, target
the earliest of now plus `bounds.recovery_minutes`, every non-due gate's
`check_at`, and every waiting unexpired registration's `expires_at`, so a
nearer real obligation is never pushed out to the bound; a pending notice
or unrelayed reservation bound equals the recovery bound and is therefore
never later. (4) Otherwise rule `schedule-as-printed` with the schedule's
`next_check_at` and `delay_minutes`. The `basis` on every write names
`schedule_reason`, `recovery_bound_at`, `earliest_non_due_check_at`,
`earliest_waiting_expiry_at`, `unrequested_due_gate_keys`,
`answered_due_gate_keys`, and `unanswered_due_gate_keys`. A failed
observation therefore never causes an immediate rerun by itself and never
delays an independent deadline; the only immediate reruns are fresh owner
work and owner-configured cadence.

The target is chosen under the store lock and applied by the harness
outside it; the one post-write fingerprint recheck narrows the window to at
most one more write and does not close it. `unavailable`, `failed`, and
`not_performed` leave the heartbeat as it was, are reported, and never
trigger a fallback cadence or a second write.

### Low-level restart and overlap

The bound `monitor enter` interface owns native restart and overlap as
described above: safe reads and observations keep the current tick across a
generation takeover, while effect-bearing actions follow their fixed restart
policy. The low-level tick interface retains its explicit abandon operation
for compatibility and tests. Exactly one tick runs per store:
`tick start` refuses `tick-in-progress`
while a record with status `running` is stored, and concurrent starts and
submits serialize on the store lock. `tick start --abandon <id>` is the only
restart path: it records the abandoned tick's pending action in
`last.abandoned_pending`, never submits a result on its behalf, sweeps its
artifact directory, and starts a new tick. By pending kind: `task_read` and
`observe` record and ingest nothing; `send` leaves the attempt `reserved`
(durable since reservation), listed in `attention` and `unresolved_attempts`
with the existing reconcile guidance, relayed by the new tick's notice as
stuck work, never re-proposed (`registration-reserved`), and settled only by
`reconcile` with target-transcript evidence; a notice `emit` leaves the
notice pending and the new tick's `emit` carries it with `replayed: true`;
`heartbeat_set` is recomputed and written by the new tick; a diagnostics
`emit` keeps its lines in `last.diagnostics_unemitted`. `restart` on the
pending action is advice (`resumable` for reads without external effect,
`abandon-only` for send, emit, and heartbeat writes); the engine cannot tell
a resumed actor from the original, and a submitted result is the actor's
assertion. A second submit for a dispositioned, unknown, or future action id
is `action-not-pending` with no change. A copied store carries its
`tick.current` and refuses until `--abandon` names it; there is no age-based
auto-abandon. `unknown-tick` and `tick-not-running` at low-level submit are
terminal for that caller: stop and start nothing. Process death after a save
leaves the pending action durable; the native monitor recovers only through
the generation-fenced bound entry.

Owner writes during a tick are allowed and unchanged: a remove or rearm
between reservation and send is caught at issue (recheck) or at report
(`attempt-superseded`); owner work landing during scheduling is caught by
the fresh-owner-work rule at issue, by the one recheck after write 1, and by
the owner's own bring-forward. Legacy commands during a tick are not refused
(compatibility), with these caveats: a legacy `cycle` can ingest
observations and reserve attempts the tick does not dispatch, which the
tick's notice relays as stuck work until their holder reports them; a
legacy `report` on a tick attempt makes the tick's later report
`attempt-superseded`; a legacy `acknowledge` of the tick's notice makes the
tick's acknowledgement `notice-acknowledged-elsewhere`; a pre-change engine
run against a store carrying tick state ignores the key entirely and can
run a legacy tick concurrently. One monitor per store, one recipe.

### What the engine enforces and what stays cooperative

The engine enforces one pending action at a time and its ordering; fully
bound arguments on every action; result shape and bounds, the read window,
monotonic tick time, and the binding of every submit to store, tick, and
action; no completion without a recorded disposition for every issued
action; internal execution of the plan cycle, result cycle, reservation,
recheck, report, notice, acknowledge, scheduling decision, fingerprint
recheck, and artifact lifecycle; no send unless the attempt is still
reserved, the read and gate evidence are fresh, and the message digest
matches; no report or acknowledgement without a submitted result; abandoned
pending sends stay reserved; at most two heartbeat writes, no fallback
cadence, and no heartbeat action without a reference; explicit abandon
before any second tick on the same store.

Cooperative only, and never verified: that the actor really invoked the
named tool or argv with exactly those arguments; the truthfulness of every
submitted result (the task-state mapping and still-this-episode judgement,
the send outcome and evidence, that emit text was printed, that a heartbeat
write happened and its `next_run_at`); that a context-lost actor abandons
rather than submitting for `send`, `emit`, or `heartbeat_set`; that no
legacy engine or adapter command runs during a tick; that owners keep their
bring-forward. Typed results are caller assertions inside the existing
trusted single-user POSIX store: no native-tool attestation, no new
authentication boundary, no hostile-same-user or distributed defence.

## Acknowledged native limitations

- No atomic idle-only conditional send. Native read and send-follow-up are
  separate tools, so the target may start running between them and a send may
  steer an already-running task. Read immediately before sending and report
  `not_sent` when the target is not idle.
- No caller idempotency token. An ambiguous send outcome is `unknown` and needs
  reconciliation against the target's transcript; the engine does not retry it.
- No atomic registry-and-send. The pre-send `inspect` recheck narrows, but does
  not close, the window in which an owner `remove` or `rearm`, or an expiry,
  lands after the check and before the send (gate and continuation are frozen
  while reserved, so no other owner change can land). The engine then records
  the outcome without overriding the owner's later state; the woken target's
  own episode revalidation is the last guard. Removal and rearm are
  cooperative cancellation of the wait, not a guarantee that no send happens.
- Observations are snapshots. Quota or Daybreak status may disappear between
  the observation and the continuation; the woken target must revalidate.
- Acceptance is not delivery. A send accepted by the tool is not evidence that
  the target received, read, or acted on the continuation.
- No unconditional delivery, model-reserve, or authentication claim. The
  routine monitor only observes metadata and authorizes no security work.
- The schedule is advisory and the heartbeat update is not atomic. Reading
  the schedule and setting the native heartbeat's next run are separate
  steps. The directed tick chooses the target under the store lock
  immediately before issuing the write and rechecks `registry.fingerprint`
  once after it, which narrows the gap without closing it: an owner change
  landing inside it is covered by the owner's own bring-forward and by the
  next tick, and the tick reports a registry that kept changing rather
  than claiming coverage. The native controls that observe, set, and
  advance the next run are the harness's, unqualified until demonstrated
  (see `native-monitor.md`).
- Results are caller assertions. Every result submitted to the directed
  tick (a read, a send outcome, that text was printed, that a heartbeat
  write happened) is the monitor's assertion about a native effect inside
  the trusted single-user store; the engine binds and orders those
  assertions and never verifies them. A missing result is never a
  performed step.
- Artifact files are not atomic with the state document. The engine's
  `plan.json` and each adapter execution's input and report files are
  sequential private writes with no transaction among themselves or with
  `state.json`; the engine reads only the pair bound in the active action after
  a submitted exit 0 and refuses any missing, partial, or invalid file as a
  failed query. A stale execution can leave files for cleanup but cannot
  supply either file consumed by the active continuation.

## Error codes

`invalid-identity`, `invalid-continuation`, `invalid-gate`, `invalid-expiry`,
`invalid-forecast`, `invalid-interval`,
`invalid-json`, `invalid-input`, `invalid-observation`, `invalid-time`,
`invalid-evidence`, `invalid-outcome`, `invalid-resolution`,
`invalid-transition`, `invalid-store`, `corrupt-store`, `store-io`,
`duplicate-target`, `unknown-registration`, `owner-mismatch`,
`nothing-to-update`, `episode-reused`, `unknown-attempt`,
`attempt-not-reserved`, `attempt-not-unresolved`, `missing-evidence`,
`invalid-adapter-report`, `unknown-notice`, and for bound monitor entry
`invalid-reference`, `registry-not-found`, `registry-mismatch`,
`monitor-active`, `stale-invocation`; for the directed tick,
`tick-in-progress`, `unknown-tick`, `tick-not-running`,
`action-not-pending`, `invalid-result`, `stale-result`, `tick-clock`.

## Worked synthetic example

An owner's end-to-end look at the engine, not a monitor procedure: three
tasks on host `h1` wait for the fictional weekly bucket on route
`route-label`. Task `t1` is idle, `t2` is running, `t3` already finished its
work. All three registered the same gate, so they share one gate key. The
block runs as written against an empty `$STORE` with no binding and no
Codex, through the legacy monitor commands (`cycle`, `report`, `notice`,
`acknowledge`) that the directed tick now runs internally: it stands in for
the query with a hand-written observation and, at the send boundary,
reports the outcome that truly happened here (no send). Its scratch
directory is the example's own; a directed tick keeps its artifacts under
the store.

```sh
GATE='{"kind":"quota_recovery","account":"acct-label","route":"route-label","bucket":"weekly","policy_revision":"policy-2026-09+0123456789abcdef"}'
for T in t1 t2 t3; do
  python3 scripts/aeon_bell.py register --store "$STORE" --owner me --host h1 --task-id "$T" \
    --episode "$T-wait-1" --gate-json "$GATE" --continuation "Quota observed open; revalidate and resume $T."
done
TICK="$(mktemp -d)"
python3 scripts/aeon_bell.py cycle --store "$STORE" > "$TICK/tick-plan.json"   # one request, task_ids [t1,t2,t3]
NOW="$(date -u +%Y-%m-%dT%H:%M:%S+00:00)"                                     # the native read time, as the monitor records it
cat > "$TICK/task-states.json" <<EOF
[{"host":"h1","task_id":"t1","status":"idle","observed_at":"$NOW"},
 {"host":"h1","task_id":"t2","status":"running","observed_at":"$NOW"},
 {"host":"h1","task_id":"t3","status":"completed","observed_at":"$NOW"}]
EOF
# Stand-in for the monitor's observe step: a real tick runs codex_status.py
# observe here and takes tick-input.json from its --output. This writes one
# open observation for the planned gate key so the example runs with no
# binding and no Codex.
KEY="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["observation_requests"][0]["gate_key"])' < "$TICK/tick-plan.json")"
cat > "$TICK/tick-input.json" <<EOF
{"observations":[{"gate_key":"$KEY","status":"ok","observed_at":"$NOW","account":"acct-label","route":"route-label",
  "buckets":[{"name":"weekly","remaining_percent":40}]}],
 "task_states":$(cat "$TICK/task-states.json")}
EOF
python3 scripts/aeon_bell.py cycle --store "$STORE" --input "$TICK/tick-input.json" > "$TICK/tick-result.json"   # one proposal, t1
ATTEMPT="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["wake_proposals"][0]["attempt_id"])' < "$TICK/tick-result.json")"
# The monitor's send boundary: the harness rechecks, reads, and sends, and the
# report carries the tool's actual outcome. This run made no send, so the
# truthful report is not_sent; t1 returns to waiting (attempt 1 of 3).
python3 scripts/aeon_bell.py report --store "$STORE" --attempt-id "$ATTEMPT" --outcome not_sent \
  --evidence-json '{"recheck":"synthetic example: no native send was made"}'
python3 scripts/aeon_bell.py notice --store "$STORE" > "$TICK/tick-notice.json"   # no --adapter-report: observe did not run
NOTICE_ID="$(python3 -c 'import json,sys; n=json.load(sys.stdin); print(n["notice_id"] if n["report"] else "")' < "$TICK/tick-notice.json")"
if [ -n "$NOTICE_ID" ]; then
  python3 -c 'import json,sys; print(json.load(sys.stdin)["text"])' < "$TICK/tick-notice.json"   # relay verbatim
  python3 scripts/aeon_bell.py acknowledge --store "$STORE" --notice-id "$NOTICE_ID"
fi
rm -rf "$TICK"
```

With that task-state file (`t1` idle, `t2` running, `t3` completed) and an
open observation, the result cycle proposes exactly one wake for `t1` and
skips `t2` (`task-running`) and `t3` (`task-completed`). The report comes
before `notice`, so the notice carries one `not_sent` event and no stuck
work; a `notice` run while the attempt is still `reserved` would list that
reservation as stuck work, which is the engine's honest view of an unreported
attempt. In a real tick the harness's recheck, read, and send precede the
report, and `report --outcome accepted` marks `t1` completed for that
episode; a simulated outcome is never reported as `accepted`. When the
observation says the bucket is still exhausted with a reset advertised for
tomorrow, nothing is proposed, and the result cycle's `schedule` plans the
next query a quarter of the way to that reset, bounded at 360 minutes from
the observation's own timestamp: six hours, not the advertised reset and not
a fixed tick. With no reset and no owner forecast it plans 60 minutes; with
an owner's `--expected-open-at` half an hour away it plans 15. A
`daybreak_status` gate closed on exhausted capacity plans the same way from
its own `reset_at` hint; closed because the model is not exposed, it plans
the 60-minute default whatever reset the bucket advertises. The three
registrations share the one gate key, so the earliest of their demands sets
the query, and the owner of any of them can bring the monitor's heartbeat
forward to that time after registering.
