# Prepare a fixture-identity and Stop-output check

This procedure proposes one disposable Claude Desktop-hosted Code task, one
setup turn, and one bounded Stop collection. Its useful result is an observed
conditional association between the independently selected task, current Code
identity, setup response, and one selected metadata file in a declared folder.
It leaves Desktop's active account/organization directory unproved.
It cannot establish incoming notification delivery, notification acknowledgment,
or full runtime preservation.

The [accepted experiment decision](https://github.com/nisavid/provingkit/issues/397#issuecomment-5972295427),
[conditional association decision](https://github.com/nisavid/provingkit/issues/476#issuecomment-6065165501),
[collector contract](collector-contract.md), and
[metadata helper contract](metadata-contract.md) control this source draft.
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
| Launcher | Exact command and inherited environment, including proposed socket, hook Code PID, hook session-ID, and optional host-task-ID observations; no implicit environment sanitization claim |
| Independent witness | Scoped normal-UI creation/selection observation and the unique setup-response text as displayed in that selected task |
| Metadata directory | Choose and review its nomination method, then bind one explicitly declared account/organization metadata folder; no active-directory claim |
| Candidate selection | Up to three explicitly selected metadata paths from the bounded listing, with the later grant covering each complete file |
| Association inputs | Exact request file, supplied UI/setup evidence, admitted Stop record, explicitly chosen `cwd` or `originCwd` relation, setup-window beginning, maximum join age, and selection/lifecycle recheck |
| Receiver effects | Task creation, one model turn, hook command, whole-event acquisition, configuration restoration, output retention, and fixture closeout |

The optional [executable prototype](executor-contract.md) can sample the ancestry
between its own PID and the hook's claimed Code PID and hash that ancestor's
opened image. An intended binary pin, installed package, or collector PID alone
does not establish the selected Code executor. Preparation must bind native role
and source compatibility independently and reconcile incomplete states with
task association. Enumerate process `stat` records, the claimed `exe` path,
byte ceilings, hook environment, reader lifecycle, and retained output in the
later grant. This source draft performs no receiver process reads.

The declared folder, independent UI witness, and executor observation remain
preparation inputs. A folder name or a matching file does not prove which
directory Desktop currently selects. If no unique conditional association can
be observed within the reviewed scope, retain that gap and return for a method
choice. The app-side projection and old receipt remain references for a specific
unresolved gap; this method adopts neither.

The [folder-nomination comparison](../../research/2026-10-10-fixture-folder-nomination.md)
leaves the method choice open: an independently supplied exact folder, or two
bounded parent-name listings after an independently supplied profile root and
an explicit account-child choice. The latter would additionally expose sibling
account/organization names and need its own reviewed selection rules and read
grant. Opaque or ambiguous names may leave the folder unresolved. Neither a
host-ID filename hint nor a later matching file proves the active directory.
The ordered steps below begin with one declared folder; they do not authorize
or select those additional parent listings.

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

If the executable extension is selected after prototype acceptance, bind its
six-process limit, 8 KiB per before/after process record, 256 MiB image ceiling
plus overflow detection, and 30-second observation wait in the packet. Use
independently assessed native bytes for comparison. A changed digest is
unassessed, not incompatible. Timeout preserves Stop but can leave reader exit
unconfirmed; the packet must specify owned-reader quiescence before artifact
removal. This cost is additional to input acquisition and publication. Total
duration remains unmeasured.

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
   match the configured token. Apply the collector contract's
   [unbound-mode interpretation](collector-contract.md#observation-meaning)
   of projection gaps and require its `unbound` evidence. Retain optional
   unbound event cwd/mode and their
   gaps without upgrading them to full runtime observations. The retained hook
   session identity is unclassified until the join; reject a `served:` identity. Compare event cwd
   with the selected project while preserving its source fallback limitation.
   Acquire only the granted run files and event
   output. Require complete JSON, recorded EOF, a valid receipt interval, and
   the matching unbound response. A claim alone, a partial file, absent output,
   or a command success message supplies no task binding. Source Stop joins and
   trims text; actual emitted representation is one of the observations sought.
6. **List, select, and acquire metadata in separate actions.** In the declared
   folder, invoke the helper's `list` operation: names and types only, up to 128
   entries plus one overflow entry. Overflow stops this attempt. Select at most
   three explicit JSON basenames under the reviewed selection rule. A candidate
   `hostTaskNomination.filename` may nominate one basename only if it appears in
   this listing; it does not independently identify the task. Missing or unknown
   nomination leaves the reviewed explicit selection method responsible for
   candidate choice, without widening the file count or searching other folders.
   Obtain the
   grant covering each whole file before acquisition. Recheck that the same
   disposable UI task/project remains selected after the setup and Stop samples.
   Invoke `associate` with the supplied witnesses, recheck, and selected files.
   Each read stops at 1 MiB plus one overflow byte. Overflow, malformed data,
   changed samples, or another required file remain gaps. The helper does not
   follow metadata paths or read transcripts. Its regular-file and identity
   checks do not establish containment through hostile ancestors.
7. **Evaluate the association.** Require the UI witness, whole setup-token
   match, observed Code identity, and exactly one current `cliSessionId` match
   among the acquired candidates, with filename equal to serialized Desktop ID
   plus `.json` and the explicitly chosen saved project relation. A saved `cwd`
   or `originCwd` match does not prove the engine's current cwd or worktree.
   Prior Code lineage alone does not match. Record separate
   collection intervals for the UI, Stop receipt, metadata reads, and executor
   witness. The helper requires a supplied selection recheck after both UI and
   Stop samples, and a maximum join age checked again after acquisition. The
   grant must bind what that recheck actually observes and the lifecycle gap it
   leaves. Missing or stale evidence yields unknown. These observations are not atomic and
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

The helper also reads the entire declared request file, up to 128 KiB plus one
overflow byte. Enumerate its witnesses, paths, and private contents in the later
grant. Listing and candidate acquisition are separate inputs; the helper
neither selects files automatically nor verifies permission to read them.

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

Use `capturing-agent-procedures` when consuming this method: load and record the
published revision of this procedure, metadata helper, collector, and any
selected executor extension, plus the folder-nomination comparison; bind entry
inputs and output meaning; record the
procedure actually used; verify completion and cleanup; return corrections to
its source. Preparation must retain the result as a conditional association,
with active-directory proof and full notification qualification separate.
Broader method codification remains with the
[agent-panel workflow catalog](https://github.com/nisavid/provingkit/issues/306).
