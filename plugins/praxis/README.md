# Praxis

Praxis is the Provingkit plugin for work stewardship: shaping, conducting,
recovering, and completing agentic efforts and improving how they run. Its
first equipment, **Aeon Bell**, supplies shared gate observation, task
registration, and conditional dispatch for gated task continuations.

## Work stewardship

An effort brings together intent, a graph of work, participants, context,
artifacts, and obligations. Praxis is the home for methods that keep those
parts coherent as work proceeds: deciding what comes next, carrying context
between participants, reconciling results, recovering interrupted work, and
recognizing completion.

That domain includes lifecycle orchestration, triage, handoff and closeout,
cross-repository work inventory, and capturing reusable agent procedures.
Those are directions for later workflows; the first increment is Aeon Bell.
Each future skill must earn a distinct invocation and compose with the owner
of any specialized operation it needs.

Praxis workflows stand alone. Wayfinder, To Tickets, and their replacements
can supply optional workflow integrations. They are not prerequisites for
using Praxis. Adopting a behavior from another skill requires its own
provenance and ownership decision.

## Aeon Bell

Shared waiting conditions come into one monitoring pass. Owners register a
task continuation against a typed gate, optionally with an expected-opening
forecast and an effective poll interval; one persistent monitor task with one
native heartbeat observes each shared condition once per tick and wakes
registered targets whose gate is open and whose task is idle. The engine
schedules the next tick from the expected wait (sparse for long waits,
tighter near likelier opening times, an explicit interval winning outright),
and the monitor sets its heartbeat's next run from that schedule. The harness
supplies scheduling controls and task control; Aeon Bell supplies the
registry, the observation adapter, the schedule, and the dispatch contract.

The engine directs the monitor through a registry-bound entry. Setup binds
the existing canonical registry, complete binding-path list, and one native
heartbeat and returns an entry reference. Each native run calls `monitor
enter`; the engine claims a newer generation and returns one bound action.
The monitor performs that action with the harness's native tool (a task read,
the adapter query with engine-owned paths, a send carrying the exact reserved
message, a print, or a heartbeat write) and passes its typed result to
`monitor continue` with the engine-issued continuation until the pass is
complete. The engine enforces one pending action at a time, bound
arguments, exact result shapes, the pre-send freshness and reservation
checks, internal notice selection and acknowledgement, the scheduling
decision (fresh owner work first, an answered gate's own deadline next, a
failed observation bounded by the recovery bound, else the schedule as
printed), at most two heartbeat writes, and generation-fenced takeover with
fixed interruption policy. An interrupted send is never replayed; its
reservation remains available for evidence-based reconciliation or an exact
late result. Whether a tool was really invoked and whether a result is true
stay the monitor's assertions; a failed step is a recorded result, a
missing result never completes a tick, an unknown send stays unresolved for
evidence-based reconciliation, and an unacknowledged notice replays.

## Public skills

| Skill | Owns | Calls |
| --- | --- | --- |
| `aeon-bell` | shared-gate-observation, task-registration, conditional-dispatch | - |

`skills/aeon-bell/SKILL.md` is the invocable entrypoint: it selects the
role and routes to one reference. An owner (register, inspect, update,
pause, remove, or rearm a gated continuation) reads
`references/engine-cli.md`, which carries the owner commands and the worked
synthetic example; the monitor (run the shared tick) reads
`references/native-monitor.md`, the complete bound-entry procedure, and
uses `references/structured-harness.md` when the client supplies serializable
structured state. The installed binding then owns opaque transport and
native-result association behind one `advance` entry point. It operates only
the registrations already in its configured store. Codex
adapters address the skill as `$praxis:aeon-bell`.

### Roster and resources

```text
plugins/praxis/
├── plugin.json                                   # Canonical Agent Plugins v1 manifest
├── .claude-plugin/plugin.json                    # Validated Claude identity projection
├── topology.json                                 # Component, call, and ownership map
└── skills/aeon-bell/
    ├── SKILL.md                                  # Role-selecting entrypoint: owner or monitor
    ├── agents/openai.yaml                        # Codex interface metadata
    ├── references/engine-cli.md                  # Engine contract, owner commands, worked example
    ├── references/codex-status-adapter.md        # Binding config, fixed protocol, outcomes
    ├── references/native-monitor.md              # The complete monitor tick procedure and quiet rules
    ├── references/structured-harness.md          # Structured binding and qualification procedure
    ├── scripts/aeon_bell.py                      # Registry, monitor cycle, and attempt engine
    ├── scripts/codex_status.py                   # Status-only Codex observation adapter
    └── scripts/monitor_binding.js                # Node-free structured harness binding
```

Both Python scripts are standard-library CLIs with no dependency outside the
skill directory. The ECMAScript binding uses no installed Node runtime or
ambient I/O; Node is only its pinned conformance runner. `aeon_bell.py` never
reads credentials, calls a service, or
executes a native task tool. `codex_status.py` runs one fixed, status-only
Codex app-server subprocess per bound route, verifies the local account
identity before and after observing and the policy revision before, and emits
typed observations that `aeon_bell.py cycle --input` consumes unchanged.
Missing local account metadata, or a server-exposed identity that contradicts
the binding, is held and never opens a gate; a server that exposes no account
identifier is observed at the lower evidence level the adapter reference
states (local metadata under the bound home plus a server-authenticated
account), never reported as a confirmed identity. The
engine's `notice` and `acknowledge` commands own what a monitor tick relays:
selection and acknowledgement are durable store state, and the monitor prints
the notice text verbatim. Binding configs
are owner-prepared private files; the plugin ships no binding values and no
policy copies. The installed `references/` are the canonical interface
documentation; `docs/praxis-engine-contract.md` is a short repository
entrypoint that links to them.

### Status of the equipment

This source snapshot establishes the installable procedure, the engine with
its adaptive schedule and directed tick, and the status adapter with
constructed tests. It also establishes the source-stage structured binding
and synthetic conformance traces, plus the controlled agent trials recorded in
`evals/praxis/aeon-bell.json`. The tick tests drive the public commands with
synthetic native results and the fake Codex executable only. Neither the
source nor those trials establish a live operating monitor, qualification of
the adapter against an installed Codex, the native heartbeat controls the
tick's heartbeat write needs, including preventing an older unreported write
from overwriting a newer generation, Luna High as the operating monitor model,
replacement coverage of any existing monitor, recovery through reserve
capacity after an account is exhausted, actual delivery of any wake, or a
released whole Kit. No tick output asserts that any native control is
qualified. Keep prior monitors until this one has demonstrated replacement
coverage.

## Composition

Praxis coordinates an effort through the specialist that owns each operation:

- **Rolecasting** owns worker topology, model and effort selection, Daybreak
  routing policy, and the harmless runnability probe. An open Aeon Bell gate
  only invites that policy's revalidation.
- **Tricritical** owns review, finding adjudication, authorized revision, and
  review-loop completion.
- **Versionkeeping** owns Git checkpoints, publication, conflicts, worktrees,
  and cleanup operations.
- **Mergecraft** owns individual pull-request recovery, publication,
  feedback, readiness, and merge workflows.
- **Artifact Customs** owns third-party component policy and lifecycle work.
- **Proseweaving** owns generic human-facing prose mechanics.

Each task retains its work and operation authority. Praxis carries context,
obligations, and results across these boundaries and invokes the appropriate
owner for the next authorized operation.

## Plugin shape

Root `plugin.json` is the canonical Agent Plugins v1 identity.
`.claude-plugin/plugin.json` projects that identity for Claude Code. Codex
reads the standard manifest's `com.openai` extension and the same skill tree.
`topology.json` is the machine-readable map of the roster, each skill's owned
operations, and its declared skill calls; its schema version belongs to
Praxis. Skill resources are discovered from the skill tree and its `SKILL.md`
links, not declared in the topology.

## Validation

From the repository root:

```sh
python -m unittest tests.test_validate_praxis
python -m unittest tests.test_aeon_bell tests.test_aeon_bell_codex_status tests.test_aeon_bell_binding
python scripts/validate_praxis.py .
```

- `scripts/validate_praxis.py` is the plugin validator. It checks the manifest
  identity and Claude projection, the topology, skill discovery and resource
  links, the Python runtime scripts and Node-free ECMAScript resource,
  inventory and portability, and the content
  lock. `tests/test_validate_praxis.py` owns it: most cases exercise it
  against temporary synthetic fixtures, and one case requires the checked-in
  source candidate to pass against its content lock.
- `tests/test_aeon_bell.py`, `tests/test_aeon_bell_codex_status.py`, and
  `tests/test_aeon_bell_binding.py` are the behavioral tests for the engine,
  status adapter, and structured binding at their public interfaces. The
  engine tests call `aeon_bell.py`'s entry point
  in-process on temporary stores, with one test running it as concurrent
  subprocesses; the adapter tests run both scripts as subprocesses with a
  fake `codex` executable on a controlled `PATH` and synthetic auth metadata.
  The binding tests use a pinned Node runner with recording adapters; installed
  operation remains V8-only. None makes live calls.
- `evals/praxis/aeon-bell.json` records controlled agent discovery and
  application trials for `aeon-bell`. Discovery ran against a controlled
  catalog, not installed automatic discovery. Each retained record binds
  digests of the exact source it ran against and of its raw report, and
  failed or superseded trials stay in the corpus rather than being dropped.
  Read each record's status and source digests before using it as evidence
  for a candidate.
- `evals/praxis/corpus.json` is the raw control-plane scenario definition
  consumed by `evals/control-plane-matrix.json`. It declares one scenario and
  its expectations; it carries no executed run, grade, or gate result.
- `release/plugin-content-locks/praxis.json` is the governed content identity.
  It pins the plugin bytes, all three public test modules, and both eval corpora.
  `python scripts/validate_praxis.py --write-content-lock .` is the only
  supported writer; run it after an authored change, then run the ordinary
  validator.

The content lock verifies source identity only. Passing validation does not
run the behavioral tests, execute or grade either corpus, prove the runtime
behaves correctly, or grant release, installation, or host-mutation authority;
inclusion in a Provingkit release needs its own evidence.
