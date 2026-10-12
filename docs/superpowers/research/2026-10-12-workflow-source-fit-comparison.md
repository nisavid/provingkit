# Workflow ownership and the four borrowed contributions

Provingkit should own the rules that decide when its agents act, ask, wait, resume, and finish. Matt Pocock's skills remain useful sources and, where they fit, optional dependencies. I recommend selecting their contributions individually: absorb the small handoff-composition contribution into Praxis's planned handoff/recovery procedure; retain Wayfinder's graph methods through a bounded optional adapter; use a bounded To Tickets derivative; and design the autonomous triage control flow under Provingkit ownership rather than describing it as an invocation-only patch.

This is a source-based recommendation for [the invocation and disposition decision](https://github.com/nisavid/provingkit/issues/189), not an accepted disposition or a performance finding. It reopens the uniform four-derivative proposal without presuming a wholesale rewrite. Repository placement, dependency selection, installation, and migration remain undecided.

## Scope and evidence

The authorized comparison covers handoff, Wayfinder, To Tickets, triage, and their directly declared prerequisites. It uses existing invocation evidence and source inspection. No experiment was rerun, no workflow was implemented, and no installed skill, configuration, or authentication was changed. The research note is the only new repository artifact.

The inspected source identities are:

- Matt Pocock's library at [`49dd158d1076134a641b33efb035946536778336`](https://github.com/mattpocock/skills/tree/49dd158d1076134a641b33efb035946536778336), observed as `main` on October 12, 2026.
- The existing Ivan-owned fork at [`7ee7f79dab48750c19c4187a9ac7f91fb6d368f6`](https://github.com/nisavid/mattpocock-skills/tree/7ee7f79dab48750c19c4187a9ac7f91fb6d368f6), also observed as `main` that day.
- The Provingkit research branch at `9474df6c1dbd0adf9361b8a19a7082e45e1b3a1e` before this note, plus the accepted decisions linked below. Current Provingkit architecture was also checked against [`CONTEXT.md` at `c1858b8621205032e3b68e73ed3e87ea34a8cd2c`](https://github.com/nisavid/provingkit/blob/c1858b8621205032e3b68e73ed3e87ea34a8cd2c/CONTEXT.md).

The completed [invocation trials](2026-10-11-user-only-skill-invocation-evidence.md), [interpretation](2026-10-11-user-only-skill-invocation-interpretation.md), and [Codex source addendum](2026-10-12-codex-explicit-skill-input-path.md) remain separate evidence. In their stated versions, assistant-written dollar text is not the traced Codex explicit-input route, and the tested Claude setting did not lift the native refusal. Those findings eliminate proposed mechanisms; they do not choose the desired policy or qualify a replacement.

This comparison was performed locally. The installed Rolecasting native-child binding covers ChatGPT Codex and Codex CLI/TUI, not this Desktop surface. No independent research worker or formal independent review is claimed. Resolving that binding belongs to Rolecasting and is not evidence that a Matt Pocock skill caused the limitation.

## Requirements that select the source

The [accepted Praxis roster](https://github.com/nisavid/provingkit/issues/158#issuecomment-6035716985), [work-structure assessment](https://github.com/nisavid/provingkit/issues/532#issuecomment-6104731630), and [evaluation contract](https://github.com/nisavid/provingkit/issues/160#issuecomment-6076287940) already establish the important distinctions:

- An authorized brief can enter directly. A named workflow, planning map, or new ticket is not compulsory.
- The steward keeps the parent outcome and remaining obligations. A completed worker contribution or planning map does not complete the effort.
- Actionable work continues within its grant. A genuine human decision, refusal, pause, no-poll instruction, or expired authority still holds the affected work.
- Transfer requires an actual receiver and a disposition, not just a useful summary. A delivered result must be consumed and reconciled before dependent progress.
- Work structure is proportional: bounded work, an adequate existing graph, a new graph, or coordination across distinct efforts. Shared external objects do not merge efforts.
- Specialist owners retain dispatch, Git, PR, review, and lifecycle mechanics. Praxis owns their effort-level joins, not replacement implementations of those mechanics.
- Discovery, instruction application, native operation, installation, and qualification are different claims. Complete costs include failed attempts and human rescue, not just successful wakes.

The current conversation adds the desired agent-invocation policy for the four contributions, coordinator and worker use within grants, separate Codex/Claude route evidence, and a continuing preference for compatible public names. To Tickets still requires approval of the delivery transition and its proposed breakdown. The other ten flagged skills remain outside the proposed policy change. The blanket derivative commitment and presumed fork-first migration path are reopened; they are not premises of this analysis.

The mismatch is therefore not simply a frontmatter flag. [The library's README](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/README.md) deliberately distinguishes user-led orchestration from model-invocable disciplines. Its invitation to adapt the skills supports selective reuse, but does not make that orchestration model fit Provingkit automatically.

## Per-contribution fit

### Handoff: absorb the composition method into the stronger owner

[Handoff's source](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/skills/productivity/handoff/SKILL.md) is a short document-writing procedure: summarize for fresh context, reference existing artifacts, name useful skills, redact sensitive material, and tailor the result to the receiver's focus. It does not perform or verify ownership transfer, return coverage, resource continuity, or unknown-effect reconciliation.

Retention would keep a human-invoked summary utility but would not satisfy the requested agent route. A small derivative could make that utility callable, yet Praxis would still need almost all of its accepted handoff/recovery behavior around it. Maintaining a separate required runtime dependency for this small contribution offers little obvious leverage.

I recommend incorporating those useful composition principles, with provenance, into the already-planned `handing-off-and-recovering-efforts`. Keep packet composition separate from transfer effects inside that owner. Temporary storage is not automatically adequate for a transfer whose lifetime requires retained evidence. This explicitly revises the earlier conditional retain-and-invoke disposition; it must be accepted before source work or retirement.

Preserve existing human use during migration. Whether the short public name remains as a compatibility entrypoint is a later delivery choice, not a reason to create a second maintained transfer procedure or silently add to Praxis's Roster. A summary-only caller and an actual transfer caller must retain distinguishable completion criteria.

### Wayfinder: retain the graph methods, not a second outer controller

[Wayfinder's source](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/skills/engineering/wayfinder/SKILL.md) provides valuable destination, frontier, fog, decision-index, claim, and dependency conventions. It also defaults to planning, limits non-research resolution to one ticket per session, and stops after charting. Planning-only is not itself wrong: the source permits an execution override, and this effort has deliberately retained a planning boundary.

The conflict arises if those session boundaries govern an already-authorized larger effort. Removing the invocation flag would not remove them. Retaining the full workflow as the mandatory outer controller would leave two competing answers to when the parent should continue.

I recommend a bounded derivative only as an optional graph/planning procedure under Praxis stewardship. Keep the representation and tracker conventions; make entry, continuation, and return obey the enclosing grant and declared planning scope. Actual stakeholder decisions still go to the human. Planning completion returns to the steward; it does not initiate implementation. The adapter must not grow its own effort ownership, dispatch service, or competing continuation ledger.

This is a plausible bounded change because the useful graph contract is separable from the entry/session rules, not because a small diff has already been demonstrated. If delivery requires recreating Praxis's control logic throughout Wayfinder, stop calling it a light derivative: retain the graph methods in a Provingkit-owned adapter instead. That is a source-disposition decision, not permission to expand the patch silently.

There is also an application problem to test. The retained [shared-intake research](2026-10-10-shared-intake-reconciliation.md) found an incident in which Wayfinder was loaded but its broader assessment was missed. Better discovery or a new source owner alone is not a demonstrated repair.

### To Tickets: the strongest bounded-derivative candidate

[To Tickets](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/skills/engineering/to-tickets/SKILL.md) supplies vertical, independently verifiable slices; genuine blocking edges; an expand–contract exception for wide refactors; and approval before ticket publication. Those methods fit the accepted delivery boundary better than an ungated replacement would.

Retention leaves the invocation problem. A derivative can change the caller policy while preserving both required approvals, tracker policy, and protection of the parent issue. Its instruction to work the frontier must be scoped to independently authorized execution; publication of an approved breakdown must not supply that authority by itself. An approved delivery transition and an approved breakdown are distinct decisions even when obtained together.

I recommend a bounded derivative when this optional transition is delivered. A new first-party ticket decomposer has no demonstrated advantage in this source comparison. It should not become a prerequisite for generic Praxis intake, handoff, or continuation, and this decision need not wait for it to be implemented.

### Triage: preserve the methods; own the autonomous control flow

[Triage](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/skills/engineering/triage/SKILL.md) combines useful verification, prior-decision recovery, redundancy checks, and agent briefs with maintainer-driven selection and a mandatory pause after its recommendation. It also assigns a human-merge meaning to a PR state. Its separate [brief reference](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/skills/engineering/triage/AGENT-BRIEF.md) and [rejection-history reference](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/skills/engineering/triage/OUT-OF-SCOPE.md) carry substantive behavior, not optional decorative examples.

Making this workflow autonomous involves policy about selection, classification, evidence, ordinary state transitions, exceptional transitions, rejection, and return after new information. It also requires composing its brief with the original grant and amendments; a posted brief cannot manufacture authority. That is more than invocation metadata.

I recommend Provingkit-owned control semantics for the optional triage integration, reusing the verified-request, durable-brief, and prior-rejection methods with attribution. Do not move the whole issue state machine into Praxis's generic intake or prescribe new repository labels. In this repository, tracker policy excludes PRs as a general request surface; the source's PR branch is therefore not a reason to add one. The source's mandatory AI disclaimer also conflicts with Ivan's current voice instruction and needs an explicit disposition if its publication procedure is adopted.

This is the least urgent first delivery: source inspection establishes a fit concern, not a measured rate or cost of triage interruptions. Keep triage outside the first increment and return with a bounded desired workflow before choosing its plugin/home. A first-party procedure can remain a clearly attributed derivative of useful text or methods; ownership of behavior is not a claim of clean-room authorship.

## Actual prerequisites and dependency scope

These are direct source edges and resources, not a selected install manifest or a whole-Kit dependency audit.

| Contribution | Declared skills and resources | Ambient and policy requirements |
| --- | --- | --- |
| Handoff | No required helper skill; suggested skills are output for the receiver. | File access, authoritative artifacts, suitable storage, and the intended receiver context. |
| Wayfinder | `grilling` and `domain-modeling`; `research` on research tickets; `prototype` on prototype tickets; additional skills named by a particular map's Notes. | Tracker policy and controls, claims/dependencies/pagination, Git publication for research artifacts, delegation for research. No unconditional To Tickets call appears in the inspected body. |
| To Tickets | No required helper-skill call in the inspected body. Its templates are inline. | Tracker and label policy, domain vocabulary/ADRs, source context, explicit approvals, and publication authority. Missing setup is an escalation, not an automatic setup invocation. |
| Triage | `grilling` and `domain-modeling` when clarification is needed; `AGENT-BRIEF.md` and `OUT-OF-SCOPE.md`. | Repository request-surface/label policy, full issue context and relevant code evidence, verification controls, prior decisions, and authorized tracker changes. |

The inspected [grilling](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/skills/productivity/grilling/SKILL.md) intentionally waits on actual human decisions and delegates factual exploration. Keep that distinction: use it for unresolved consequential choices, not every ordinary continuation. [Domain modeling](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/skills/engineering/domain-modeling/SKILL.md) is an active model-changing discipline with glossary/ADR formats; merely reading the repository vocabulary does not require it. The caller must not turn every planning return into another model-editing exercise.

[Research](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/skills/engineering/research/SKILL.md) requires a background agent and a source-backed Markdown capture. [Prototype](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/skills/engineering/prototype/SKILL.md) selects its [logic](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/skills/engineering/prototype/LOGIC.md) or [UI](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/skills/engineering/prototype/UI.md) resource. Artifact production and source capture still require the enclosing task's authority. Selecting either method does not authorize implementing its eventual answer.

These reusable disciplines are candidates to retain, not evidence that every skill in the library belongs in every deployment. The practical classification is per caller: deployed procedure requirement, development/evaluation aid, optional integration, or historical source contribution. Adoption of a method into owned source need not leave a live external call. A real external call needs a selected revision, complete applicable resources, discovery, behavior evidence, and an update owner. The complete caller inventory and install selection remain later work.

## What the existing fork changes

There is already an Ivan-owned fork. Its current [packaging procedure](https://github.com/nisavid/mattpocock-skills/blob/7ee7f79dab48750c19c4187a9ac7f91fb6d368f6/docs/agents/plugin-packaging.md) preserves upstream skill bytes and invocation settings. Its [builder](https://github.com/nisavid/mattpocock-skills/blob/7ee7f79dab48750c19c4187a9ac7f91fb6d368f6/scripts/build-plugin-package.mjs) generates a native Codex manifest selecting the original promoted directories and requires the source manifest to match the promoted inventory. It neither produces a curated four-skill selection nor changes their control semantics.

The inspected fork is a useful possible delivery vehicle, not an already-qualified answer. No build, compatibility test, installation, or workflow evaluation was run here. Reusing that vehicle still requires source selection, provenance/reconciliation policy, appropriate package identity, and verification that active discovery does not resolve a competing copy. Importing the whole promoted set merely because the packaging exists would reverse the requirements-first decision.

Praxis should own the accepted effort contract. Provingkit should decide which contributions its actual consumers need. Source maintenance can live in the existing fork or an owning plugin after that selection; Base Loadout and Host Binding Profile keep their established selection/materialization roles. This research defines no new manifest dependency mechanism and selects no new Slate member.

## Smallest useful delivery increment

I recommend one bounded, first-party Praxis path from an authorized direct brief through a returned contribution to resumed parent progress. Include the shared intake assessment, handoff composition/recovery, and the necessary steward/closeout behavior for that path. Use existing specialist owners for their operations. Do not begin by modifying all four public skills or building the whole planned cohort.

The discriminating case is an effort with a known parent obligation, one authorized worker contribution, and independent useful work. The parent consumes the worker's complete applicable result, preserves remaining obligations, and continues without asking the human merely to resume. Add an interruption or transfer that checks retained intent, grant, holds, receiver acceptance, and resource continuity. A companion case contains a real undecided human choice: only its dependent work remains held, and silence never supplies the answer. If no supported return route exists, the expected result is a truthful uncovered handoff, not invented continuation.

This is a proposed future slice, not a new evaluation allocation. It needs a currently supported, separately evidenced harness route. The Desktop Rolecasting gap blocks a claim through that missing binding, not all source preparation or an independently supported route. Do not infer a binding or change surfaces silently. Preserve the accepted predecessor and adoption constraints through [adoption sequencing](https://github.com/nisavid/provingkit/issues/161).

For later authorized evidence, compare unchanged equipment, invocation-only changes, and the proposed control contract where each arm is supported. Retain required specialist reviews in every arm. Measure completion and complete result consumption, unnecessary human interventions, needless planning, lost obligations, unsafe progress, and total attempt costs. The [accepted evaluation owner](https://github.com/nisavid/provingkit/issues/160#issuecomment-6076287940) selects workload-specific limits, repetitions, holdouts, and scoring before qualification. Source analysis supplies no numeric winner.

Follow that direct-input slice with the optional Wayfinder mapping of the same effort, then the independent portfolio case. This is staged evidence, not removal of the [accepted three-part proof set](https://github.com/nisavid/provingkit/issues/159#issuecomment-6063591613) or permission to claim the whole cohort from one route. To Tickets remains a later approved transition; autonomous triage remains a separate integration increment.

## Decision and delivery handback

The next decision is whether to adopt this mixed disposition direction, including the amendment from optional external handoff utility to an owned composition contribution. Exact source arrangement follows that decision. Compatible public-name handling remains explicit; nothing here authorizes renaming, retiring, or shadowing an installed skill.

For future iterations, keep a contribution external while its behavior fits and its update/qualification cost is justified. Own it when control semantics diverge substantially or the external call adds more coordination than reusable behavior. A derivative is not automatically temporary, and a useful retained dependency need not have a retirement deadline. Replace either when current evidence and consumer migration justify it, not because the library is foreign or a similarly named replacement exists.

Artifact Customs retains source admission and disposition records; the procedure owner retains behavior and upstream reconciliation; Rolecasting retains route/dispatch support; evaluation and adoption retain their accepted owners. Later delivery must capture the maintained procedure, connect actual callers, verify reviewed-revision loading and checked results, and qualify the claimed routes before cutover. The current research completes the comparison only. It does not settle the invocation decision, close its ticket, or change the planning map.
