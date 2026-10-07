# Native harness bindings

Aeon Bell requires bindings for Codex native heartbeats, Claude Routines, and
Cursor Automations. Each uses the harness's own scheduler and task controls.
The shared engine supplies the registry and directed tick; a binding supplies
the actual execution, storage, task, output, and scheduling interfaces.

## Select the execution surface

During setup, record three separate choices:

- **Hosting scheduler**: the native product and execution surface that run
  the monitor, with one stable scheduler definition per canonical registry.
- **Continuation target**: the harness and task class whose current wait can
  be read and whose existing conversation can receive a continuation.
- **Gate provider**: the account and route whose status the observation
  adapter can actually query.

Support for one choice does not establish the other two. The shipped
`codex_status.py` observes Codex routes; running it from another harness does
not observe that harness's quota. Package discovery and generic control
injection do not supply native scheduling or continuation controls.

Select one hosting binding for a registry. The three required bindings are
alternatives for operating that registry, not three concurrent monitors.
Record the exact product, source revision, native control interfaces, runtime,
registry identity, and supported target/provider combinations. Keep a missing
interface visible as unsupported rather than inventing a substitute service
or silently dropping a required harness.

## Persistent configuration and fresh runs

The scheduler definition and canonical registry persist. A native product may
start a fresh conversation or workspace for each scheduled run. Restore the
reviewed engine and binding source, configured entry reference, and actual
native controls through that product's supported configuration channels.
Verify access to the same canonical registry and its required locking and
artifact storage; a fresh repository clone or editable automation memory is
not that registry.

Give each native invocation fresh structured run state. Continue the same
state slots within that invocation. A later native run enters through the
configured entry and lets the engine perform takeover; it never reuses a
previous invocation's run slot or reconstructs an old continuation from text.
The binding's structured state does not replace the durable registry.

## Native controls and evidence

Bind each interface from a documented or directly observed native contract:

| Interface | Required observation |
| --- | --- |
| Engine execution | Exact argv and output transport, process completion, and positively not-started versus ambiguous outcomes |
| Registry access | The same canonical store and configuration across native firings, including interrupted-run takeover |
| Task read | Current native task state and latest-turn evidence relating it to the registered wait episode |
| Continuation send | Exact reserved bytes to the existing target, preserved worker settings, and accepted/not-sent/unknown outcomes |
| Notices | Verbatim engine-selected output and quiet behavior on unchanged, non-actionable passes |
| Scheduling | The same native scheduler definition, observed next run, adaptive absolute deadline, owner bring-forward, and truthful failure results |
| Model and capacity | Actual surface controls and observed limits, under Rolecasting's maintained selection policy |

State precision, timezone, recurrence, late or missed runs, overlap, suspension,
and capacity limits from the selected surface. A native recurring schedule
does not establish an absolute next-run setter or authoritative readback.
An unconditional update does not establish newer-write ordering.
[Native monitor operation](native-monitor.md) owns the ordering acceptance
scenario and activation gate, including an older write whose result is lost.

For Claude, distinguish [cloud Routines](https://code.claude.com/docs/en/routines),
self-hosted execution, and Desktop Local scheduled tasks. Bind eligibility,
registry access, schedule updates, and target messaging on the chosen surface;
CLI availability alone establishes none of them. Session-scoped cron is a
different facility.

For Cursor, bind [Automations](https://cursor.com/docs/cloud-agent/automations)
and their chosen managed or self-hosted execution route. Establish the target
class separately: a Cloud Agent continuation interface does not establish
access to local IDE or CLI conversations. Automation memory and a native cron
expression alone establish neither canonical registry access nor Aeon's
scheduling contract.

## Delivery status and joins

This source contains the common engine, structured binding factory, and Codex
status adapter. Complete native bindings are still to be implemented and
qualified for all three required harnesses:

| Required binding | Native adapter and controlled evidence | Installed native evidence |
| --- | --- | --- |
| [Codex native heartbeat](https://github.com/nisavid/provingkit/issues/456) | Status adapter and common synthetic controls; complete native binding absent | Scheduling, target continuation, persistence, and ordering unqualified |
| [Claude Routines](https://github.com/nisavid/provingkit/issues/457) | Complete native binding absent; common tests supply no Claude-specific evidence | Chosen execution surface, scheduling, target continuation, persistence, and ordering unqualified |
| [Cursor Automations](https://github.com/nisavid/provingkit/issues/458) | Complete native binding absent; common tests supply no Cursor-specific evidence | Chosen execution surface, scheduling, target continuation, persistence, and ordering unqualified |

Update the affected row when its source or evidence changes. For each binding,
report source implementation, controlled tests, actor application, installed
native behavior, and activation separately. Retained historical trials and
current unexecuted cases stay distinct from fresh observations. Reuse common
evidence only for unchanged shared behavior; qualify surface-specific claims
on that actual surface and source revision.

All three bindings require implemented source, controlled conformance, and
bounded disposable native integration evidence before the Praxis candidate
lands. Their preparation can proceed independently of the Praxis shell.
Freeze the composed candidate before final application evidence and review;
composition or a changed evidence dependency invalidates affected passes.

Production activation remains a separate join. The selected binding must
demonstrate native ordering and consumer replacement coverage before replacing
existing monitors. A green source test, injected control, package projection,
or submitted `applied` result cannot satisfy that join.
