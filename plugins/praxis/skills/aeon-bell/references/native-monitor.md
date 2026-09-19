# Native monitor operation

The complete procedure for the one persistent native task that runs the Aeon
Bell monitor pass. The engine directs the pass: it issues one fully bound action at a
time (a task read, the adapter query, a send, a print, a heartbeat write)
and the monitor performs exactly that action with the harness's own native
tool and submits the typed result. The harness supplies scheduling, task
reads, send-follow-up, and printing; this reference binds them to the
engine's contract without adding authority. Paths are relative to the skill
directory. `engine-cli.md` is the engine's full contract for interpreting
any output (its "Directed tick" section defines every action and result);
its owner commands and worked example are the owner's reading, not part of
this procedure.

## Structured execution

A harness with serializable structured state must use
[`structured-harness.md`](structured-harness.md). Its installed binding owns
entry, continuation, action arguments, native-result association, result JSON,
and transport retry. The actor sees only its bounded display and supplies only
an issued decision id plus one allowed semantic choice. It never copies an
opaque reference, argv, message, heartbeat target, or native result through
text. If the harness cannot inject the configured entry and state through
those channels, stop unsupported before `monitor enter`.

The command sequence below defines the engine contract and remains the path
for a harness that has no structured binding support. It is not permission to
replace a supported binding with actor transcription.

## Role and inputs

The monitor observes and dispatches; owners register. Setup binds the
canonical existing `$STORE`, the complete configured list of `$BINDING`
paths, and the one `$HEARTBEAT` into an engine-issued `$ENTRY_REF`. The native
run receives only that entry reference. It never selects a store, binding,
heartbeat, tick, action id, replay, or abandon path.

The registry must already exist unless setup deliberately uses
`--initialize-registry`. Runtime `monitor enter` opens it without creation
and checks its canonical path, stable registry id, and configuration revision.
An empty binding list is valid configuration: a due gate then records
`no-binding`, relays the gap once, and stays quiet while unchanged. The
heartbeat reference is an opaque label for the harness's existing control;
the engine does not interpret it.

The other inputs are the native task read, send-follow-up, print, and
heartbeat controls, and the clock. When the harness supplies a logical time,
pass the same `--now` to `monitor enter` and every `monitor continue` for that
invocation; otherwise omit it everywhere. The engine refuses a mix as
`tick-clock`.

The registrations already in `$STORE` are the whole of the monitor's work.
The owner commands (`register`, `update`, `pause`, `resume`, `remove`,
`rearm`) belong to the task that owns each registration and are never run by
the monitor, whatever a tick finds: a tick with nothing waiting is a
successful no-op, and stuck work is relayed by its `next_action` for its
owner to act on. Ownership is cooperative (the engine checks `--owner` to
prevent accidental cross-owner edits), so this separation is kept by
following it, not by authentication.

Configuration the invocation needs but does not have is reported as the
engine records it. A missing registry is `registry-not-found`; a stale or
altered binding is `registry-mismatch`; a due gate with an empty configured
binding list is the standing `no-binding` condition. The invocation invents
no store path, label, policy revision, continuation, credential, binding
value, or heartbeat reference.

## Setup

- Bind the existing registry once and keep the returned entry reference in
  the native monitor configuration:

  ```sh
  python3 scripts/aeon_bell.py monitor bind --store "$STORE" \
    [--initialize-registry] [--registry-id "$REGISTRY_ID"] \
    [--binding "$BINDING"]... --heartbeat "$HEARTBEAT"
  ```

  Use `--initialize-registry` only for deliberate first setup. Reconfiguration
  supplies the current registry id and is refused while an invocation is
  active. Entry references prevent accidental misbinding; they are not
  credentials or proof of the native task.
- One persistent monitor task per store with exactly one native heartbeat
  that performs the tick below. The heartbeat has no fixed cadence: each
  tick ends with the engine choosing its next run from the registry's
  freshest schedule (see "Scheduling decision" in `engine-cli.md`), sparse
  for long waits and tighter near likelier opening times, with an owner's
  explicit interval winning outright. Never create per-run or
  per-registration cron tasks, and never create automation per tick or per
  registration; the one heartbeat is updated in place.
- The operating monitor model is Luna High, qualified before it operates:
  activation waits for that qualification, and Luna Low is not activated
  meanwhile.
- Before activation or cutover, the harness must demonstrate, on this one
  heartbeat, the native controls the `heartbeat_set` action needs:
  observing its next run, setting the next run to an absolute time, and
  advancing a later or suspended run to an earlier time (the owner's
  bring-forward). It must also start an older write A, apply a newer-generation
  write B, and then let A finish after B, both when A reports a result and when
  A's result is never submitted. The control must reject or serialize A,
  terminate or cancel it within a bound, and authoritatively observe B as the
  final target. If any control or proof is absent or fails, report the concrete
  missing control, leave activation and coverage unqualified, and do not
  fall back to a frequent fixed heartbeat or treat the owner's
  bring-forward as optional. This reference names no native parameter and
  assumes no recurrence-rule support; the harness's own controls are used
  as they are. No tick output ever asserts that these controls are
  qualified: a submitted `applied` result is the monitor's assertion, not
  evidence. Engine generation fencing, binding state, manual recovery, and an
  unconditional setter that receives generation data do not satisfy this
  ordering gate.
- The native heartbeat inherits the monitor task's model and may substitute an
  unavailable model. Whether a heartbeat uses reserve capacity after quota
  exhaustion is unqualified; do not rely on it either way. A resumed worker
  keeps its own model and effort; nothing here overrides them.
- Keep any prior monitors running until this monitor has demonstrated
  replacement coverage for their registrations. Coverage is shown by
  registrations, observations, and reported attempts in `inspect`, not by
  the monitor existing.
- Supplying a binding the monitor lacked, or fixing one the adapter refused,
  is a change the already-scheduled heartbeat does not notice on its own. A
  gate requested with no `--binding` at all (`no-binding`) or left
  `unhandled` by the adapter has been deferred by the engine to the liveness
  bound whatever its owner's explicit interval, and a tick whose query
  failed set its next run as the engine's recovery rule chose; that run
  stands until it fires. After adding or fixing a binding, bring the
  existing heartbeat forward or run its tick explicitly, under the same
  native authority the owner's bring-forward uses, and do not create a
  second heartbeat. Coverage of the affected gates begins with that tick,
  not with the file landing, and a gap clears only when that tick's query
  answers the gate: a supplied binding whose query fails leaves the gap
  standing and the next run at the liveness bound, so fix it and bring the
  heartbeat forward again. If the harness cannot advance the run, report
  the concrete missing control as this section already requires; a tick
  that ran and applied its schedule prints nothing about it.
- Tick artifacts belong to the engine. When a query is due, the engine
  writes `plan.json` under `$STORE/ticks/<tick_id>/` (directory `0700`,
  file `0600`) and names that directory's `input.json` and `report.json` in
  the adapter argv it issues; the adapter writes both with mode `0600`.
  The monitor creates no temporary directory and writes no file of its
  own. The engine removes the directory when the tick completes or is
  superseded and sweeps stale ones at every `monitor enter`; a directory it
  could not remove is a diagnostics line, never silently left. The store
  stays the only durable record.

## The monitor pass

The monitor uses only `monitor enter`, `monitor continue`, and the redacted
`monitor status`. Every other engine or adapter command is outside this
recipe while a pass runs. The engine may still accept legacy commands for
compatibility; the monitor never invokes them.

1. Enter with the configured reference:

   ```sh
   python3 scripts/aeon_bell.py monitor enter --entry-ref "$ENTRY_REF" [--now "$NOW"]
   ```

   This atomically claims a newer invocation generation and returns either
   `complete` or one `action_required` with an engine-issued continuation.
   Entry handles interrupted work by fixed policy: reads and observations
   retain their tick and are safely reissued through a continuation bound to
   the new generation, so a pending pre-send read keeps its reservation and
   rechecks it normally; an interrupted send retains its reservation and is
   not replayed; a notice or diagnostics emit is replayed; and a heartbeat
   write is recomputed. Older continuations remain fenced. The actor makes no
   restart decision.
2. For each `action_required`, perform exactly the returned action with the
   named tool or argv and no other arguments, then submit its result:

   ```sh
   python3 scripts/aeon_bell.py monitor continue \
     --continuation "$CONTINUATION" \
     --result-json '<result in action.result_shape>' [--now "$NOW"]
   ```

   Each kind uses the same result contract:

   - `task_read`: read the target named by `host` and `task_id` with the
     native task read tool and map its state truthfully as "Task-state
     mapping" describes, judging the `episode` named in the arguments.
     Result `{"status": ..., "observed_at": <read time with offset>}`. In
     supplied time mode give `observed_at` the same logical time as
     `--now`; the engine accepts a read stamped from 60 seconds before the
     action was issued to 60 seconds after now (`stale-result` otherwise).
   - `observe`: run `argv` exactly as printed. Result `{"exit_code": 0}` or
     `{"exit_code": 2, "stderr_line": "<the verbatim codex status line>"}`.
     The engine reads the adapter's files from its own directory and
     refuses any missing, invalid, or partial file as a failed query; the
     monitor never reads, copies, or edits them.
   - `send`: send `message` verbatim with the native send-follow-up tool to
     `host` and `task_id`, with no model or effort override. Result
     `{"outcome": "accepted|not_sent|unknown", "evidence": {...}}` exactly
     as the tool answered: `accepted` is acceptance by the tool, not
     delivery; `not_sent` is a refusal before any effect; `unknown` is an
     ambiguous answer (timeout, partial failure, unclear response), which
     the engine leaves unresolved for `reconcile`.
   - `emit`: print `text` verbatim, with no paraphrase, reordering, or added
     state. Result `{"emitted": true}`.
   - `heartbeat_set`: set the next run of the heartbeat named by
     `heartbeat` to `target_at` with the harness's own control. Result
     `{"applied": true, "next_run_at": <the run the control left>}`; the
     engine records a run that differs from the target by more than a
     minute as `applied-off-target` and reports it.

   If the action could not be performed, submit the failure form instead:
   `{"disposition": "not_performed|failed|unavailable", "reason": "<concrete reason>"}`
   (`not_performed`: the tool or argv was not invoked; `failed`: invoked
   with no interpretable answer, which for a send the engine records as
   `unknown`; `unavailable`: the tool or control does not exist for this
   target or heartbeat). A failed step is an explicit recorded result; a
   step whose result is never submitted leaves the invocation running and can
   never count as done.
3. `invalid-result`, `stale-result`, or `tick-clock` leaves the same active
   continuation available for a corrected result. `stale-invocation` means a
   newer entry fenced this actor: stop and start nothing. The only exception
   is an effect the actor actually performed from its exact old continuation;
   submit that result once. The engine records it when still applicable and
   returns `stopped` without another continuation. Never infer or submit a
   result for an effect the actor did not perform.
4. Use status only for diagnosis:

   ```sh
   python3 scripts/aeon_bell.py monitor status --entry-ref "$ENTRY_REF" [--now "$NOW"]
   ```

   Status is redacted and cannot resume work. It never returns a continuation,
   action id, action arguments, target, message, notice text, binding, or
   heartbeat. Start a native run with `enter`; do not reconstruct work from
   status.
5. The pass is done when the result is `complete`. Print nothing beyond what
   `emit` actions carried. A routine pass that relayed no notice and met no
   failure prints nothing, and there is no periodic status line.

The engine runs the plan cycle, the result cycle, reservation, the pre-send
recheck, the report, notice selection, acknowledgement, the scheduling
decision, and the artifact lifecycle itself between actions; the monitor
composes no command, path, id, or text. What it does assert, and the engine
cannot check, is that the named tool was really invoked with exactly those
arguments and that each submitted result is true.

An open `daybreak_status` gate only invites the owner's policy revalidation.
It never proves the route is genuinely runnable and never replaces the
harmless probe that Rolecasting requires before Daybreak work.

## Task-state mapping

Every `task_read` action names one registration's target. A native status is
evidence about the task, not proof the task still wants this continuation.
Supply `idle` only when all hold:

- the native status is idle;
- the task's latest turn is still this registration's wait for the
  `episode` named in the action (no later turn completed, abandoned, or
  replaced the waiting work);
- the task is not waiting on a human;
- the task is not canceled, archived, or unavailable.

Otherwise supply the truthful state: `completed`, `canceled`, `archived`,
`human_waiting`, `running`, `unavailable`, or `unknown`. The engine skips every
non-idle state and records the reason. A registration whose target has moved
on belongs to its owner to remove or rearm; the tick relays it and does not
send.

Observed times are the read time, with a UTC offset. A task state older than
15 minutes when the engine judges it is unknown to the engine, whether at the
result cycle or at the pre-send read: a send is never issued from a read
that has aged past that window, however it was stamped.

## Sending a wake

A `send` action is issued only after the engine has, in one locked
transition, taken the `pre-send` read you submitted as idle and still fresh,
confirmed the gate evidence the attempt was reserved against is still
fresh, rechecked that the registration is still `reserved` under this
`attempt_id` and `episode` and unexpired, and matched the message digest the
attempt persisted. Send exactly what the action carries and submit exactly
what the tool did. The tool can steer a running task and offers no atomic
idle check and no idempotency token; the engine's immediate recheck and
your immediate read are the only guards, and an owner remove or rearm, an
expiry, or a target state change landing after them and before the send is
not prevented. The engine records the outcome without overriding the owner's
later state; the target's own episode revalidation is the last guard.

The wake message tells the target that the wake authorizes no work and that it
must revalidate its own episode, eligibility, quota, and policy before
continuing. An open `daybreak_status` gate invites that revalidation; it never
proves the route runnable and never replaces the harmless probe.

An `unknown` outcome is settled only by
`reconcile --attempt-id "$ATTEMPT" --resolution accepted|not_sent --evidence-json '{...}'`
after checking the target transcript, outside any tick. Never resend on a
guess.

## Quiet rules

Report to the owner or operator only when the tick produced something to act
on. The engine decides that: its notice step compares the store (and this
tick's adapter report) with the baseline it last acknowledged and issues an
`emit` with the literal text to relay, and it acknowledges that notice when
you submit that the text was printed. The monitor keeps no marker list in
its context and paraphrases nothing. See the Notification state section of
`engine-cli.md` for the contract.

### What the notice selects

- **Events**: attempt resolutions the baseline has not acknowledged, with
  the delivery claim (`accepted_by_native_send_tool` is acceptance by the
  tool, not delivery) and the next action. A wake sent and reported in
  this tick is one event; a resolution that happened days before a restarted
  monitor's first tick is still one event. Superseded attempts are not.
  An event's gate labels are the gate the attempt was reserved against, even
  when the owner has edited the registration's gate since.
- **Standing conditions**, reported on first sight and on change:

| Condition | Source | Marker |
| --- | --- | --- |
| Stuck work: a registration `reserved`, `unresolved`, or `expired`, or an outstanding attempt whose registration was removed (`detached`) | `attention` | registration id, status, `since` |
| Configuration gap: a gate a waiting registration uses that every binding passed to the query left `unhandled` (`binding-labels-differ`) | the adapter report's `gates` | gate key |
| Configuration gap: a gate a waiting registration uses that a tick requested with no `--binding` passed at all (`no-binding`; configuration knowledge from the tick's own inputs, not a query answer) | the tick's `requested_gate_keys` and `no-binding` | gate key |
| Provider hold or failure: a gate a waiting registration uses whose last result was `held` or `error` | `retry_schedule` | gate key and reason code |

  A hold or failure is one standing condition keyed by its cause: the first
  sight and a changed reason code are news; an identical re-result after
  backoff, the advancing failure count, and the moving `next_due_at` are
  not; a successful observation, or nothing waiting on the gate any more,
  clears it. A gap or failure that left is reported as cleared once, because
  the same condition can return and must then read as new. Stuck work that
  left drops silently: its closure was the owner's command or this monitor's
  own submitted result. A gate due again is the engine asking for an
  observation, not a condition newly eligible for notification.

A notice whose `emit` you could not perform stays pending: the engine
reports `notice-unrelayed` in its diagnostics, the next tick's `emit`
carries the same notice with `replayed: true`, and it is acknowledged only
after you submit that it was printed. Repetition until acknowledgement is
the contract (at least once, never dropped); nothing here proves that a
person received the text.

### Stuck work and the actor who may close it

`attention` in `inspect` is the one list of stuck work: `unresolved_attempts`
is the same attempts in attempt-level detail and never holds an entry
`attention` lacks, and an empty registrations list with a nonempty
`attention` list is stuck work, not a no-op. An unchanged entry is never
dropped by the engine: it stays in `inspect` until it is reported,
reconciled, rearmed, updated, or (for a registration with no open attempt)
removed.

Every `reserved` or `detached` entry names two paths, and which one applies
depends on what the actor knows, not on what is convenient:

- The tick that holds the reservation observed the send outcome and submits
  it as the `send` action's result (or, when it refused before sending, the
  engine already recorded `not_sent` from the read or recheck). For a
  detached entry the engine records `not_sent` with
  `{"recheck": "registration-removed"}` itself.
- A restarted monitor, a new monitor task, or an owner finding a reservation
  it did not make (including one left by an abandoned tick's pending
  `send`) has no send knowledge. It checks the target transcript for the
  exact message and runs
  `reconcile --attempt-id "$ATTEMPT" --resolution accepted|not_sent --evidence-json '{...}'`
  with that evidence, outside any tick. It never reports `not_sent` on a
  guess: the registration would return to `waiting` and the next open
  observation would send a second wake for the same episode, a blind retry
  of a send that may already have reached the target.

For a detached entry the registration stays `removed` whatever the outcome.
An `unresolved` or `expired` entry is the owner's: the tick relays its
`next_action` and leaves the registration as it is.

### Worked example: an unchanged configuration gap

Registration `R` waits on gate key `K` (kind `quota_recovery`, labels
`acct-label` and `route-label`), and no binding passed to the tick carries
those labels.

- 02:00. The tick requests `K` (`unobserved`) and issues `observe`; the
  adapter reports `K` as `unhandled`, `binding-labels-differ`, so the
  submitted exit 0 answers nothing for `K` and the result cycle skips `R` as
  `gate-unobserved`. The notice step finds `unhandled:K` new and issues
  `emit` with the kind, labels, and `R`; after the print is submitted the
  engine acknowledges it. The heartbeat write targets the liveness bound,
  08:00: the gate stays due, but no binding can answer it, so the engine's
  schedule defers it and the tick's recovery rule does not apply.
- 08:00. The same request, report, and skip. The notice step is quiet: no
  `emit`, nothing printed. The repeated request and skip are the engine's
  observation state, not a second notification.
- 08:30. The monitor task is restarted and its context is empty. Still
  quiet: the baseline is in the store, not in the context, and the
  heartbeat write is the same recommendation the store gave before.
- Later, a binding with those labels is passed and `K` is observed. The
  notice step issues `emit` with `cleared: unhandled gate ... K`; printed,
  acknowledged. If that binding is withdrawn again, `K` reads as new again.
- If, instead, `K` is simply not in a tick's query set (a fresh cached
  observation of another gate, a backoff window, or a tick whose query was
  not issued), the engine keeps `unhandled:K` as retained knowledge and
  stays quiet: no query, no new knowledge.
- If no `--binding` is passed at all, the tick runs no adapter and learns
  `no-binding:K` from its own inputs: reported once as `new: no-binding
  gate ...` with `K`'s kind, labels, and `R`, deferred to the liveness
  bound the same way (a nearer expiry or another gate's planned check still
  wins), quiet on every later identical tick and after a restart, and
  cleared once a binding's query answers `K` (an `unhandled` answer clears
  it and is new in the same notice). No adapter report, observation, or
  capacity is claimed for a query that was never issued, and a supplied
  binding whose query fails clears nothing.

Say nothing for an empty registry with an empty `attention` list, unchanged
closed gates, gates inside their backoff window, targets that are simply
still running, and a heartbeat write that applied as chosen; the engine
already does. The generated text names the gate kind, labels, registration
and attempt ids, statuses, `since`, reason codes, and next actions, and
never observation values, binding values, host or task ids, episodes,
continuation text, or store contents; relay it as is and add none of those.
The diagnostics `emit` at the end of a tick carries only engine codes, the
adapter's own redacted error line, ids, times, and counts.

## Importing an outside observation

When another source already observed the same tuple (equivalent condition,
route and account labels, and policy revision) and its observation is still
fresh, an operator may import it instead of querying, through the legacy
`cycle --input` command between ticks (never during one): add it to
`observations` with its original `observed_at` and `expires_at`. The engine
keeps that expiry when it is shorter than 15 minutes from `observed_at` and
clamps it to that window otherwise: an import may shorten freshness but
never extend it, whatever reset time the source advertised. An imported open
observation that is still fresh admits eligible work at the next tick's
result cycle, ahead of any planned check; an imported closed one becomes the
new anchor, and its `reset_at` is only a scheduling hint for the next
planned query. Both hold only when the import is newer than what the store
already holds for that gate key: an import whose `observed_at` is earlier
than the stored successful observation or the key's last recorded failure
is superseded and skipped (`observation-superseded`), and one stamped at the
same second preserves the stored observation (`observation-not-newer`), so
an older or unordered import never moves the anchor backward, never clears
a newer failure, and never admits from evidence the store has already
passed. Check the `ingested_observations` entry rather than assuming the
import applied.
