# Coordinator history trace for the cross-examination round

This input is supplied only after first-round outputs are frozen. It records the coordinator's source and tracker audit; it is not an independent first-round lane.

## What was done

At c1d77f8dd6a5dab58f6dfd96275dff0ea6015ae0, the published observer-probe source contains a ten-replacement patch for one manager JavaScript archive member and an added CommonJS helper. The helper bundles desktop-adapter.mjs, observer-contract.mjs, and observer-probe.mjs. Hooks cover module loading, query install/teardown, Code-session identity changes, observed permission-mode events, and manager attachment. candidate-build.json says runtimeExecuted:false. packaging-evidence.md records an offline candidate build, independent ASAR extraction, unchanged-member verification, and syntax checks. It states the modified app has not been loaded. No installation or live observer experiment was performed in this task. The later fixture-identity receipt at this revision is a design, not implemented code.

The operational proposal replaces the installed app.asar while Desktop is stopped, preserves its executable/assets/launcher, starts the candidate with the existing signed-in profile, then stops it, restores the pristine archive, and starts original Desktop. Two restarts can interrupt active tasks; the total window is unmeasured. This is temporary application package modification, not a hot patch of a running process. Receipt design would acquire exact fixture identity after metadata persistence and keep the setup within one candidate/restored launch pair. It adds hooks, private acquisition/recovery records, and a 15-minute acquisition-admission ceiling, without bounding total restoration time.

## Decision sequence

- [First contract](https://github.com/nisavid/provingkit/issues/192#issuecomment-5845461915): notify an exact existing Desktop Code peer, receiver-origin delivery plus explicit correlated acknowledgment, before/after actual account/model/permissions/worktree evidence, live disposable idle/busy proof.
- [Inbox feasibility](https://github.com/nisavid/provingkit/issues/213): inspected native MCP ListAgents/SendMessage and performed read-only discovery; receiver evidence remained open.
- [Evidence path](https://github.com/nisavid/provingkit/issues/249#issuecomment-5881568334): retained Desktop and chose automated evidence, documented APIs first; internal format adoption returned separately.
- [Automated evidence research](https://github.com/nisavid/provingkit/issues/262#issuecomment-5882874123): metadata/transcript reader plausible, effective settings and selected sender's actual receiver evidence unresolved.
- [Reader adoption](https://github.com/nisavid/provingkit/issues/271#issuecomment-5884146675): conditional source adoption with graduated compatibility; new version unassessed, not incompatible.
- [Observation paths](https://github.com/nisavid/provingkit/issues/272#issuecomment-5885945293): concrete saved-file paths, but saved selections insufficient for full effective runtime claim.
- [Observer direction](https://github.com/nisavid/provingkit/issues/273#issuecomment-5886197304): preserve full claim, applied permissions includes mode/rules/grants/pending changes, start read-only surfaces then consider app adapter; patching returns for adoption.
- [Observer design](https://github.com/nisavid/provingkit/issues/274#issuecomment-5886784164): compares saved files, host MCP get_session, renderer LocalSessions IPC, existing query controls. Proposes app-side selected export; missing fresh account/current cwd/complete applied permissions remain.
- [Prototype direction](https://github.com/nisavid/provingkit/issues/276#issuecomment-5887014877) and [acceptance](https://github.com/nisavid/provingkit/issues/277): source/synthetic observer and insertion plan accepted as probe-plan input, no installation authority.
- [Probe preparation](https://github.com/nisavid/provingkit/issues/278): implemented source candidate, offline package build, synthetic checks, bounded review cycles, launch/restoration procedure. No live run.
- [Receipt direction](https://github.com/nisavid/provingkit/issues/341#issuecomment-5922511522), [design](https://github.com/nisavid/provingkit/issues/352#issuecomment-5923725775), [acceptance](https://github.com/nisavid/provingkit/issues/353#issuecomment-5925012453): add an exact newly-created-task identity mechanism, latest adoption conditional on this broader scope review.

## Scope audit

There was meaningful narrow source research and alternative comparison. The retained material does not establish a deliberately broad independent conceptual first round, independent third-party survey, frozen exchanges, and cross-informed follow-up before choosing instrumentation. Reviewing the chosen observer's correctness or security does not establish that it is the simplest architecture. Successive source decisions do not replace that comparison.

The central question is what each obligation needs: message transport, positive receipt evidence, before/after effective-state evidence, and qualification-fixture acquisition are separable. Strong evidence requirements may drive app changes without proving them necessary or sufficient. Any reduction of the accepted claim must be an explicit operator decision.
