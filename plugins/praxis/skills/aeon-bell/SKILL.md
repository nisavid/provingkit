---
name: aeon-bell
description: Use when a task must wait on a shared external condition (a quota bucket recovering, a Daybreak model becoming available) and continue later through the shared Aeon Bell registry, when an owner must inspect, update, pause, remove, or rearm such a registration, or when running the shared monitor tick. A single-task delay is a timer, not a gate; pull-request follow-up belongs to Mergecraft; model and route policy belongs to Rolecasting.
---

# Aeon Bell

Shared external conditions, observed once per tick, waking registered task
continuations. Owners register; one monitor observes and dispatches; the
engine reserves every attempt before a send and selects what the monitor
relays. Paths are relative to this skill directory. `$STORE` is the private
registry directory for one user on one machine, conventionally
`${XDG_STATE_HOME:-$HOME/.local/state}/praxis/aeon-bell`.

## Which role is this invocation?

Decide first. Each role reads one reference and runs only that role's
commands.

- **Owner**: this task, or a task it acts for, must wait on a gate and
  continue later, or must inspect, update, pause, resume, remove, or rearm a
  registration it made. Read [engine-cli.md](references/engine-cli.md): its
  "Owner commands" section is the recipe, and its worked synthetic example
  runs as written against an empty `$STORE` with no binding and no Codex.
- **Monitor**: this invocation is the shared monitor task, or is asked to run
  one monitor pass. Read [native-monitor.md](references/native-monitor.md).
  When the harness supports structured serializable state, also read and use
  [structured-harness.md](references/structured-harness.md); it is the required
  execution path and keeps opaque values out of actor text. Stop unsupported
  before entry when its exact structured source, entry, state, or adapter
  channels are absent. Bind the
  existing registry, binding paths, and one heartbeat explicitly during
  setup; runtime entry never creates a missing registry and accepts no
  per-run store, binding, heartbeat, tick, action, replay, or abandon choice.
  The engine owns takeover, interruption handling, and generation fencing.
  The monitor composes no command, path, id, or text of its own and prints
  nothing on a routine pass that relays no notice and meets no failure.
  Registering, editing, removing, or rearming a wait is owner work, whatever
  a pass finds.

The engine checks `--owner` on owner commands to prevent accidental
cross-owner edits; the roles themselves are separated by these instructions,
not by authentication.

## Vocabulary

- **Gate**: a typed JSON condition. `quota_recovery` opens when the named
  bucket has remaining capacity; `daybreak_status` opens when the model is
  exposed with available capacity. `account` and `route` are safe local
  labels; `policy_revision` binds the routing policy revision together with
  an opaque digest of the private identity binding, so a changed binding
  changes the gate.
- **Gate key**: SHA-256 of the gate. Equivalent gates share one observation
  and one query per tick.
- **Observation**: a typed snapshot from a status adapter, fresh for 15
  minutes. Freshness is the maximum age that may open a gate, not a polling
  interval: when a gate is next queried is the engine's schedule.
- **Schedule**: the engine's recommendation of the next check, computed from
  the latest successful observation's timestamp and the owners' metadata,
  never from a remembered tick. A closed gate is requeried after a quarter of
  the estimated remaining wait (an owner forecast or an observed reset hint),
  bounded 15 to 360 minutes, or 60 minutes with no estimate; an owner's
  explicit interval wins outright. A due gate is due now.
- **Registration**: owner, host, task id, episode, gate, bounded continuation
  text, expiry (24 hours by default, 7 days at most), and optional cadence
  metadata: an expected-opening forecast and an effective poll interval that
  the authorized caller already resolved from operator or policy
  requirements. One active registration per host and task.
- **Episode**: one wait. A wake completes it; waiting again needs `rearm`
  with an episode identity the registration has never used.
- **Attempt**: reserved before any send, then reported `accepted` (by the
  send tool, which is not delivery), `not_sent`, or `unknown` by the monitor
  holding the reservation; anyone without send knowledge reconciles with
  target-transcript evidence, never a guess.
- **Notice**: the engine's selection of what a tick must relay, frozen in
  the store until acknowledged. The monitor prints its text verbatim as the
  `emit` action the tick issues; the engine acknowledges it once that
  result is submitted.
- **Tick**: one engine-directed pass. The engine issues one bound action
  at a time (`task_read`, `observe`, `send`, `emit`, `heartbeat_set`) and
  the monitor submits exactly that action's typed result or the failure
  form; a failed or unavailable step is a recorded result, a missing one
  leaves the tick unfinished, and every result is the monitor's own
  assertion about a native effect, never verified by the engine.
- **Monitor entry**: the configured registry-bound interface for a native
  run. Each `enter` claims a newer generation; `continue` advances only the
  issued action, and `status` is redacted and never resumes work. Entry and
  continuation references prevent accidental misbinding; they are not
  authentication or execution proof.

An open `daybreak_status` gate only invites the owner's policy revalidation.
It never proves the route is genuinely runnable and never replaces the
harmless probe that Rolecasting requires before Daybreak work.

## References

- [engine-cli.md](references/engine-cli.md): owner commands and the worked
  synthetic example; the full command, gate, cycle input and output, attempt
  lifecycle, notification state, error codes, and acknowledged limitations.
- [native-monitor.md](references/native-monitor.md): the complete monitor
  procedure: role and inputs, task setup, the tick, task-state mapping, the
  send and reconcile boundary, and the quiet rules.
- [structured-harness.md](references/structured-harness.md): the structured
  binding load, advance, classification, retry, stop, and qualification
  procedure for clients with serializable state channels.
- [codex-status-adapter.md](references/codex-status-adapter.md): the private
  binding config, the fixed status-only Codex protocol, outcome reasons, and
  what the adapter refuses to do.
