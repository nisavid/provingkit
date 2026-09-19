# Praxis Aeon Bell architecture and interface entrypoint

Aeon Bell is the first and only equipment of the Praxis plugin: shared gate
observation, task registration, and conditional dispatch for gated task
continuations. Its canonical interface documentation is installed with the
skill and is the single API reference; this page only orients a reader and
links to it.

## Components

| Component | Canonical reference |
| --- | --- |
| Skill procedure for owners and the monitor | [`plugins/praxis/skills/aeon-bell/SKILL.md`](../plugins/praxis/skills/aeon-bell/SKILL.md) |
| Engine `scripts/aeon_bell.py`: registry, monitor cycle, directed tick, attempt lifecycle, error codes | [`references/engine-cli.md`](../plugins/praxis/skills/aeon-bell/references/engine-cli.md) |
| Status adapter `scripts/codex_status.py`: binding config, fixed protocol, outcomes, redaction | [`references/codex-status-adapter.md`](../plugins/praxis/skills/aeon-bell/references/codex-status-adapter.md) |
| Native monitor task: setup, task-state mapping, send and reconcile, quiet rules | [`references/native-monitor.md`](../plugins/praxis/skills/aeon-bell/references/native-monitor.md) |
| Structured harness binding: exact-value transport, classification, retry, qualification | [`references/structured-harness.md`](../plugins/praxis/skills/aeon-bell/references/structured-harness.md) |

## Architecture

One persistent monitor task observes each shared condition once per tick, at
a cadence the engine schedules from the expected wait. The engine owns the
registry, the schedule, and the dispatch contract: it consumes typed JSON
observations and task states, plans the next check from the latest
observation and the owners' metadata, reserves every attempt before a send,
and emits structured proposals. It directs the monitor through a bound
interface: setup binds one existing canonical registry, its binding paths,
and the shared heartbeat; `monitor enter` claims a newer generation and
issues one fully bound action at a time (a task read, the adapter query with
engine-owned paths, a send with the exact reserved message, a print, or a
heartbeat write); and `monitor continue` accepts the action's typed result or
failure form through an engine-issued continuation. Takeover safely reissues
reads and observations under a new generation while retaining their tick,
proposal, reservation, and engine-owned artifacts; older continuations remain
fenced, and the existing result path performs every normal recheck. Takeover
retains an uncertain send reservation without replay, replays durable output,
and recomputes scheduling. `monitor status` is redacted and cannot resume work.
The status adapter turns the engine's observation requests into typed
observations from one fixed, status-only Codex query per bound route. The
harness supplies the native heartbeat and its scheduling controls, task
reads, send-follow-up, and printing. Both scripts are Python
standard-library CLIs with no dependency outside the skill directory.
Clients with serializable structured state use the Node-free
`scripts/monitor_binding.js` consumer. It retains engine and native values
behind one `advance` interface and exposes only a redacted classification
view. It does not change engine replies, prove native effects, or supply
heartbeat ordering authority.

## Trust boundary

The engine never reads credentials, calls a service, or executes a native task
tool. The adapter reads only the account identity metadata and status endpoints
its reference names, holds any gate whose identity evidence is missing or
mismatched, and never opens a gate on held or errored observations. Registry
records carry no executable content, and diagnostics never echo store, input,
or observation values. Owner identity is cooperative local metadata, not
authentication. In the directed tick the engine enforces the ordering,
binding, generation fencing, shape, and consequences of every action and result; whether the
named tool was really invoked and whether a submitted result is true remain
the monitor's assertions inside the trusted single-user store, never
verified or attested. The acknowledged native limitations (no atomic
idle-only send, no idempotency token, snapshot observations, acceptance is
not delivery, non-atomic heartbeat and artifact writes, results as caller
assertions) are enumerated in the engine reference.

## Verification surfaces

- `scripts/validate_praxis.py` validates the plugin source contract and its
  content lock, `release/plugin-content-locks/praxis.json`.
- `tests/test_validate_praxis.py` owns that validator.
- `tests/test_aeon_bell.py`, `tests/test_aeon_bell_codex_status.py`, and
  `tests/test_aeon_bell_binding.py` cover the engine, adapter, and binding
  through their public interfaces against constructed fixtures.
- `evals/praxis/aeon-bell.json` is the public behavior-evaluation corpus.
- `evals/praxis/corpus.json` is the raw control-plane scenario definition, not
  executed model evidence.

The content lock binds source bytes; it does not run these tests or assert
runtime behavior. See [`plugins/praxis/README.md`](../plugins/praxis/README.md)
for the current status of the equipment.
