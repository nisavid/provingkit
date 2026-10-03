# Prepare the fixture collector and receiver-state observations

The source candidate supplies a command that collects one bounded Stop event
and a draft procedure for identifying a disposable Desktop task from its setup
response. The parallel access investigation separates what that event can show
from runtime observations that require the app's existing query or additional
producers. The candidate is ready for source review; a live proposal still needs
selected-executor evidence, exact acquisition paths, integration bytes, and
review of its private-data controls.

The [accepted experiment decision](https://github.com/nisavid/provingkit/issues/397#issuecomment-5972295427)
controls this increment. The
[collector task](https://github.com/nisavid/provingkit/issues/407) and
[runtime-state investigation](https://github.com/nisavid/provingkit/issues/408)
join in [probe preparation](https://github.com/nisavid/provingkit/issues/278).

## What the collector supplies

Read the [command contract](../prototypes/receiver-evidence/collector-contract.md)
and [fixture procedure](../prototypes/receiver-evidence/fixture-check-procedure.md)
before consuming the source. The command accepts an explicit configuration,
a Linux stdin pipe, and a task-owned output slot. It acquires at most the
configured event limit plus one overflow byte, records EOF/timeout/overflow,
and publishes one complete JSON result without replacing an existing result.
A retained claim prevents automatic reacquisition of a second event.

The first setup event has no independently known Code identity. The command
therefore retains its observed hook session identity, exact setup text, optional cwd/mode,
and allowed socket environment value as unbound observations. It does not feed
that observed ID back as an expected ID. Later comparison with the independently
selected UI task and authorized metadata is still necessary. The configured-ID
mode provides a partial projection for a caller-supplied identity; neither mode
authenticates the producer or qualifies the route.

The setup response is distinct from a notification acknowledgment. No sender
runs here, and no incoming message is observed. The Node process selects only
the named socket variable in application code, but its inherited environment
exists before that code runs. Exact launcher/environment review remains part
of live preparation.

The command's timeout covers pipe acquisition. It does not bound all filesystem
operations. A signal can leave a claim/partial file, or a complete result with
an unknown exit outcome. The procedure requires inspection and cleanup of the
recorded run artifacts without automatically retrying the setup turn.

## What the runtime investigation establishes

The [runtime access report](2026-10-03-receiver-collector-sources/runtime-first.md)
traces producers, actual access paths, selection, footprints, and intervals
against retained Desktop, SDK, and Code source identities. Its byte anchors and
hashes allow the investigation to be checked without treating an installed
package as the selected running executor.

| Obligation | Source result | Remaining limit |
| --- | --- | --- |
| Existing selected query | SDK control getters operate on an already owned query; the Desktop manager holds the ordinary task's query | No external passive attachment was established. Direct-connect initialization POSTs to `/sessions`; resume and reinitialization are not substitutes for passive attachment |
| Account | Spawn-bound identity/org and initialization/status credential metadata exist | No authoritative observation binds an actual inference's authenticated account to this query and credential epoch |
| Model | Selected, configured/applied, context-resolved, and some fallback values have distinct producers | No complete bound observation of the actual model for a particular attempt follows from one session value |
| Applied permissions | Code rule/directory state, event-time mode, Desktop grant evaluators, and several pending stores are identifiable | No complete aggregate; cached grants can expire and pending predicates omit some categories |
| Worktree and cwd | Registered association, pending moves, status display, and Stop cwd are distinct | The cwd helper can fall back to the original directory. Event-time cwd does not supply arbitrary endpoint provenance |
| Fixture identity | UI setup response, observed current Code ID, selected metadata, and socket observation can be joined prospectively | Actual executor, independent selected task, and unique current-Code association must still be observed |

The native inbox queues peer input. It is not a demonstrated transport for SDK
control getters. An app-side observer could address access to the selected query
and grant evaluators; it cannot create missing account/model/permission
semantics. Temporary instrumentation and an ongoing dependency remain options
for that named access gap, each requiring a concrete design, costs, and separate
selection. The old patch, restart count, and receipt deadline are not inherited.

Individual request/response and host projections have separate intervals.
Before/after query and lifecycle checks can detect replacement; they do not
make an atomic snapshot or establish an interval-wide invariant. Full actual
account/model/applied-permissions/worktree/cwd evidence remains required for
qualification and affected requalification.

## Cross-examination and verification

The [retained first findings and exchange](2026-10-03-receiver-collector-sources/README.md)
record the frozen inputs and integration. The runtime lane read no collector
output before its first report. One preliminary transport finding reached the
coordinator before the collector freeze; the complete report arrived during
snapshot preparation and did not change those frozen files. The exchange is
not described as a wholly blind coordinator integration.

Cross-examination identified a concrete mismatch: the proposed fixture could
compare optional event cwd/mode, but initial unbound collection discarded them.
The revised command retains those fields with bounded values and explicit
gaps while preserving unbound identity. It also excludes known served-call
identities, removes an unmeasured pending-byte counter, and keeps the association
observations in separate intervals and outcome facets. Capture-window rules
remain explicit for configured and unbound input. The existing pure projector and browser
demonstration are unchanged.

The agreed command test boundary covers real command invocation with invented
stdin, a selected synthetic environment, output, exit status, and disposable
files. The revised collector has 16 checks; the 20 reader/projector checks remain
in place. Node.js 24.21.0 ran all 36 successfully. A stalled-input regression
checks process termination as well as the emitted result: the initial `fs.read`
approach wrote a timeout result but remained alive until EOF; the inherited-pipe
`net.Socket` implementation passes that check. No receiver was involved.

These checks establish source/synthetic behavior over the documented inputs.
They do not establish live hook loading, producer authenticity, private-data
protection, task binding, delivery, or preserved runtime state. Independent
review must use the final candidate and renew affected evidence after changes.

## Preparation still required

The fixture proposal has a defined order and bounded discovery: one supplied
account/organization directory, no more than 128 nonrecursive entries plus one
overflow entry, and up to three explicitly selected metadata files of at most
1 MiB plus one overflow byte each. Reading those files acquires every serialized
field within the bound. Selecting fewer output fields does not reduce that
acquisition.

The preparation join must now resolve or chart these concrete prerequisites:

- Bind the actual selected executor and its compatibility evidence to the fixture.
- Establish the account/organization directory and independent UI/project witness
  without widening private discovery implicitly.
- Produce exact hook settings, launcher/environment, run paths, observation
  footprint, restoration, and fixture disposition for the later grant.
- Review the integration and relevant privacy/security controls together before
  presenting the authorization packet.

Separate later work must resolve authenticated account, executing-model
coverage, complete applied permissions, endpoint cwd/mode, and selected-query
access. Those qualification gaps do not alone prevent proposing a smaller
fixture check. Missing fixture binding or executor evidence does prevent that
check's claimed result.

Use `capturing-agent-procedures` when preparing or consuming this source. Record
the reviewed revision, actual entry inputs, observation meanings, completion,
and cleanup evidence; return useful corrections here. Installation and broader
method codification remain unselected. No private receiver reads, hooks,
installation, tasks, prompts, restarts, or notifications were performed.
