# Prepare a fixture-identity and Stop-output check

This procedure proposes one disposable Claude Desktop-hosted Code task, one
setup turn, and one bounded Stop collection. Its useful result is an observed
association between the selected task, current Code identity, and setup response.
It cannot establish incoming notification delivery, notification acknowledgment,
or full runtime preservation.

The [accepted experiment decision](https://github.com/nisavid/provingkit/issues/397#issuecomment-5972295427)
and [collector contract](collector-contract.md) control this source draft.
[Prepare and review the disposable observer probe](https://github.com/nisavid/provingkit/issues/278)
must reconcile the parallel runtime-state access design, review the final
candidate and effects, and bind the remaining inputs before presenting a live
proposal. The authorization ticket must record an actual positive grant.

## Inputs that preparation must bind

| Input | Required binding before a live proposal |
| --- | --- |
| Candidate and runtime | Published collector and projector bytes, Node executable/version, relevant Desktop/SDK source identity, and a concrete way to observe the executor actually selected |
| Dedicated project | Exact project directory and normal UI selection; no existing user task is the fixture |
| Configuration | Exact project `.claude/settings.local.json`, its current bytes or verified absence, and the single added Stop-hook entry |
| Collector slot | New private run directory and exact config, output, claim, and partial paths; expected pre-state and retention disposition |
| Launcher | Exact command and inherited environment, including the single proposed `CLAUDE_CODE_MESSAGING_SOCKET` observation; no implicit environment sanitization claim |
| Independent witness | Scoped normal-UI creation/selection observation and the unique setup-response text as displayed in that selected task |
| Metadata directory | One explicitly supplied and independently bound account/organization directory under the selected profile; do not search private settings to discover it |
| Candidate selection | Up to three explicitly selected metadata paths from the bounded listing, with the later grant covering each complete file |
| Receiver effects | Task creation, one model turn, hook command, whole-event acquisition, configuration restoration, output retention, and fixture closeout |

The collector does not identify its engine parent. An intended binary pin,
installed package, Node executable, or collector PID does not establish the
Code executable actually running the selected task. Preparation must consume
the parallel access design and propose the smallest concrete executor witness.
Any needed process/executable observations require enumerated paths/fields in
the later grant; this draft performs none.

The independently bound metadata directory and executor witness are still
preparation inputs, not discovered facts. If neither can be supplied within a
reviewable scope, retain the specific blocker rather than expand discovery.
The old app-side receipt remains an alternative for a named unresolved gap.

## Configuration proposal

The project settings change adds one entry under `hooks.Stop`. Its command
invokes the pinned Node executable and `collector.mjs`, passing the two bound
file paths as literal arguments. The approval packet must contain the final
escaped command and complete added JSON subtree, not a template to execute.
No settings installer is implemented by this increment.

For initial acquisition, configure `expectedCodeId: null`. Choose a fresh run
identifier and exact setup-response token, set `since` to the beginning of the
reviewed setup window, and bind stdin byte/time limits in the packet. A suggested
initial command limit is 1 MiB and 5 seconds; neither is a receiver execution
deadline. The hook must be configured before the setup response whose Stop is
being observed. Do not create a query only to obtain an ID and silently spend
another unapproved setup turn.

Before making the eventual change, retain the authorized pre-change bytes and
check the relevant hook settings/trust semantics for the selected executor.
Merge the single entry while preserving other hooks and settings. An existing
hook can itself act on the event, so its presence and proposed treatment must
be part of review. If a setting or policy prevents this hook, stop; do not relax
permissions to force activation.

The public [Desktop shared-configuration documentation](https://code.claude.com/docs/en/desktop#shared-configuration)
and [hook contract](https://code.claude.com/docs/en/hooks#hook-input-and-output)
support proposing a project hook. The retained
[producer findings](../../research/2026-10-02-reader-hook-findings.md#what-the-prototypes-supply)
trace Stop production and command dispatch. Neither establishes loading by the
selected live executor. A fresh disposable session avoids assuming that an
existing query reloads configuration, but it does not prove successful loading.
No Desktop restart is selected by this draft. If one proves necessary, its
effects, quiet window, restoration, and duration return for review and grant.

## Proposed ordered live steps

These steps are prospective. Source acceptance, a closed ticket, or this file
does not authorize them.

1. **Bind the grant and pre-state.** Match the published candidate, selected
   runtime, exact acquisition scope, UI observations/actions, one setup prompt,
   output retention, restoration, and stop conditions to the positive grant.
   Record what was present before any change. Use one live executor. Coordinate
   any shared-desktop window with the separately owned Computer Use work.
2. **Stage the run and add the one hook.** Create the granted task-owned files
   and merge only the reviewed entry into the selected project settings.
   Verify the resulting bytes. No claim, partial file, or output may preexist
   for this slot. The command starts only through the authorized fixture hook.
3. **Create and select the fixture in normal UI.** Observe only the granted
   controls and region. The witness must show the dedicated project and selected
   disposable task. Task titles, timestamps, a new filename, and an asserted
   environment label do not replace this witness.
4. **Submit the exact setup prompt once.** Proposed content is: “Reply with
   exactly `FIXTURE:<fresh-run-token>` and no other text. Do not use tools.”
   The final packet substitutes and approves the actual token. Record submission
   uncertainty without trying again. This is a model turn, not a cross-harness
   notification. Additional turns or changed text need a new scoped decision.
5. **Observe the response and collector result.** The selected UI response must
   match the configured token. Retain optional unbound event cwd/mode and their
   gaps without upgrading them to full runtime observations. The retained hook
   session identity is unclassified until the join; reject a `served:` identity. Compare event cwd
   with the selected project while preserving its source fallback limitation.
   Acquire only the granted run files and event
   output. Require complete JSON, recorded EOF, a valid receipt interval, and
   the matching unbound response. A claim alone, a partial file, absent output,
   or a command success message supplies no task binding. Source Stop joins and
   trims text; actual emitted representation is one of the observations sought.
6. **Acquire only the selected metadata candidates.** In the one bound
   account/organization directory, read names nonrecursively up to 128 entries
   plus one overflow entry. Overflow stops this attempt. Choose no more than
   three explicit candidate files under the reviewed selection rule. Read each
   only up to 1 MiB plus one overflow byte; overflow, malformed/incomplete data,
   changed identity, or additional required files remain gaps. Never follow
   paths found inside the metadata or open unrelated transcripts.
7. **Evaluate the association.** Require the UI witness, whole setup-token
   match, observed Code identity, and exactly one current `cliSessionId` match
   among the authorized candidates, with the expected project and Desktop
   metadata identity. Prior Code lineage alone does not match. Record separate
   collection intervals for the UI, Stop receipt, metadata reads, and executor
   witness. The grant must specify a selection/lifecycle recheck, or the result
   must retain that check as unavailable. These observations are not atomic and
   do not establish that the same query or socket is current after the event.
   Report UI/Code association, event-time endpoint association, actual executor,
   activation/collection, and restoration separately. Event-time endpoint
   association needs a present bounded endpoint from the admitted invocation
   and the independent join; executor success needs its own witness. A partial
   UI/Code match cannot stand for the combined result. This does not
   prove global uniqueness outside the acquired set, producer authenticity, or
   a functioning sender. A conflicting or ambiguous association remains unknown.
8. **Restore and close out.** Remove the specific added hook before allowing
   further fixture turns. Re-read authorized settings, compare the introduced
   subtree, and remove only that entry while preserving concurrent changes.
   Restore full pre-change bytes only if the entire current file is exactly the
   known post-change version. If the file was originally absent, delete it only
   when no unrelated content has appeared. Otherwise report the conflict and
   preserve it. Confirm no further collector invocation is in progress through
   the reviewed lifecycle observation; do not kill a reused PID. Retain the
   agreed evidence, remove only recorded task-owned run artifacts, and complete
   the granted fixture disposition. Verify those results on failure too.

The metadata reads acquire complete serialized objects, potentially including
titles, settings, reminders, grants, summaries, errors, remote/MCP details, and
other serializer fields. The [identity report](../../research/2026-10-02-reader-hook-sources/identity-first.md)
describes that footprint. Only identifiers in retained output does not mean
only identifiers were read. No account/organization discovery, bulk transcript
reader, SDK directory helper, or native `ListAgents` call is part of this proposal.

## Interpretation and recovery

Keep acquisition completion, collector exit, task association, endpoint
observation, executor identity, and settings restoration as separate results.
If the command's outcome is lost, inspect already authorized run files before
considering another action. The claim intentionally consumes the slot after
failure. Do not clear it automatically or resubmit the setup prompt. An abrupt
termination may leave a partial file; preserve its failure evidence without
interpreting it as completed collection.

The claim and output cannot demonstrate uninterrupted collection history.
This is one proposed setup-event check, not a standing monitor. Neither a
recent file read nor replaying the event can freshen its source text. Hook
exit/EOF behavior and effects on the selected receiver need observations.

The procedure has no measured total duration. Its acquisition limits concern
the collector and selected file reads. The earlier receipt's 15-minute ceiling
and two-restart window apply only if that different procedure is selected again.

## Join and completion contract

Freeze the collector, tests, this procedure, and first findings before exchanging
them with the runtime-state lane. Cross-examine selected-task/executor binding,
what a Stop record means, acquisition versus retention, proposed effects,
restoration, and which missing state producers this experiment can actually
test. Review the final revised candidate, including relevant security and
private-data controls, before producing an authorization packet.

The preparation ticket must name each still-unbound input and either resolve it
within existing authority or chart its specific decision/read grant. It must
not promote this parameterized draft into a ready live procedure. Full account,
model, complete applied permissions, and worktree/current-cwd observations remain
qualification obligations; a small fixture check need not supply all of them.
Delivery and notification acknowledgment still require later exact-peer consent.

Use `capturing-agent-procedures` when consuming this method: load the reviewed
revision, bind entry inputs and output meaning, record the procedure actually
used, verify completion and cleanup, and return corrections to its source.
Broader method codification remains with the
[agent-panel workflow catalog](https://github.com/nisavid/provingkit/issues/306).
