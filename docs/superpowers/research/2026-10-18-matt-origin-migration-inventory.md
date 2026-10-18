# Matt-origin migration: source inventory and proposed ownership

I recommend migrating coherent workflows into their Provingkit behavior owners, beginning with a bounded handoff-and-recovery path, while assessing the uncovered engineering, decision-development, and agent-authoring responsibilities in parallel. The inventory covers the complete current source tree, not just the four skills that prompted the strategy change. It does not claim that every contribution has a final disposition or that a replacement is ready to install.

The [accepted migration strategy](https://github.com/nisavid/provingkit/issues/189#issuecomment-6250854847) is the decision source. This research answers [Inventory Matt-origin contributions and map their Provingkit owners](https://github.com/nisavid/provingkit/issues/647), under [Plan Praxis’s broader work-stewardship cohort](https://github.com/nisavid/provingkit/issues/140). Proposed ownership below is an assessment, not owner acceptance, a new plugin declaration, or a change to the release Slate.

## What the inventory establishes

The companion [source inventory](2026-10-18-matt-origin-source-inventory.json) records every tracked file at `mattpocock/skills` revision `49dd158d1076134a641b33efb035946536778336`, observed on October 18, 2026. It includes Git blob identities, SHA-256 digests, sizes, source classes, skill resources, manifest inclusion, invocation metadata, and bounded local-copy comparisons.

| Source surface | Count | Meaning |
| --- | ---: | --- |
| All tracked files | 190 | Complete tree enumeration at the named revision |
| Skill entrypoints | 38 | 27 promoted, seven in-progress, four misc |
| Supporting skill resources | 27 | Templates, scripts, examples, and references, separate from entrypoints |
| Client metadata files | 38 | One `agents/openai.yaml` per skill |
| Other tracked files | 87 | Repository conventions, source-scope decisions, documentation, history, distribution, automation, license, and indices |

The plugin manifest selects 27 skills, not all 38 files named `SKILL.md`. The in-progress README omits `chief-of-staff`, which is present in the tree. `resolving-merge-conflicts` has a documentation page but no current skill entrypoint; its historical contribution is still relevant to Versionkeeping. These are reasons to inventory the tree and consumers rather than treat a menu as the dependency boundary.

I read all 38 current entrypoints and selected connected references. Every tracked supporting file is indexed and content-bound; a complete semantic disposition of every paragraph, example, helper, and external reference remains work for the selected migration slices. No source helper was executed, no invocation trial was rerun, and no installation was changed.

The evidence is source inspection and local filesystem observation. The installed Rolecasting native-child binding does not cover this Codex Desktop surface, so this inspection was local. It is not an independent review, a behavior evaluation, or native route qualification.

## Baselines and coverage limits

| Baseline | Identity or observation | What it supports |
| --- | --- | --- |
| Current Matt source | [`49dd158d1076134a641b33efb035946536778336`](https://github.com/mattpocock/skills/tree/49dd158d1076134a641b33efb035946536778336) | Complete tracked-file inventory; source contract and relationship inspection |
| Provingkit research checkout | `cb4ab576326f6d219e80d698b490939039424857` | Existing owner contracts and historical disposition records inspected here |
| Provingkit remote main | `fc50152d2d53cf9b50db4202d1c4506765d65fa4` | Observed remote ref; not a claim that every file at that revision was reviewed |
| Ivan’s Matt-source fork | `8b3fa27d9922e70c9881df4251f490aae75a8702`; observed main `7ee7f79dab48750c19c4187a9ac7f91fb6d368f6` | Existing source arrangement, not a new derivative implementation; the checked branch’s changes against its main concern fork/setup documentation |
| Dotfiles | `f226009eacd25bd1143482c8e0b0744ac010a104` | Maintained routing and authoring callers inspected below |
| Personal skill directories | 24 current-source skill directories found | Every source-listed member of those directories matched current source; presence does not prove which provider a harness resolves |
| Codex and Claude Matt marketplace caches | Both named `1.3.1`; all 38 source entrypoints present and matching | Both caches contain more files than the 27 manifest-selected skills; neither discovery nor support for in-progress/misc follows from presence |
| Claude install metadata | Enabled Matt marketplace entry; recorded source revision `f3fc5632f401156837ee3872f14fe33ccf1024ea` | Recorded installation identity, distinct from current upstream main |
| Codex configuration | Matt marketplace entry enabled | Configuration observation only, not a new invocation receipt |

The personal directories contain the 27 promoted skills except `implement-spec`, `pr`, and `retro`. Both marketplace caches differ from current source in `skills/engineering/wizard/template.sh`, although `wizard/SKILL.md` matches. The current template changes terminal clearing, existing-value handling, assignment after writing, and the enclosing execution function. This is a source diff, not a claim about which version ran or whether either version is safe.

The copy comparison checks source-listed members, not extra local files. It covers these three local surfaces, not every host, marketplace, stale cache, repository-local installation, or historical revision. The separate curated Codex cache visible in the harness catalog was not established as an active provider. Existing trial evidence remains version- and route-bound; [the earlier Codex input-path research](2026-10-12-codex-explicit-skill-input-path.md) was not rerun or broadened.

## Contribution-to-owner assessment

Each row names material to assess and preserve or adapt, not a one-to-one replacement skill. Source paths and resources resolve through the companion inventory and the immutable source revision above. “Unsettled home” means a responsibility needs design; it does not propose silently dropping the material. Existing specialist contracts remain controlling where a contribution crosses their boundary.

### Work stewardship and decision development

| Source skill | Contributions to carry into the assessment | Proposed home and boundary |
| --- | --- | --- |
| `ask-matt` | Outcome-based routing; read the relevant procedure before advising a skip; phase boundaries; continue, fresh context, compact, or hand off according to the work | Praxis owns effort routing and context decisions; specialists own the invoked procedures. Do not carry over a mandatory human-selected chain. |
| `wayfinder` | Destination; decision graph; fog versus a specifiable question; claims; native dependencies; resolution pointers; parallel research; one source for each decision | Praxis work-structure and planning integration. Preserve graph semantics without requiring Wayfinder for direct intake or imposing its session limit on every workflow. |
| `to-tickets` | Complete vertical slices; genuine prerequisites; expand–contract for wide changes; approved breakdown; native tracker relationships; parent preservation | Praxis owns delivery planning and the approved transition. Tracker policy and actuators retain mutations. Existing transition and breakdown approvals remain. |
| `triage` | Context and prior-answer recovery; reproduce claims; search for existing behavior and rejected concepts; explicit readiness; durable acceptance brief; distinct built-versus-rejected outcomes | Praxis candidate intake/readiness responsibility, with tracker policy and domain specialists. Do not inherit one tracker’s labels, AI disclaimer, or PR-ready meaning as universal policy. |
| `handoff` | Source-grounded context packet; important decisions and references; current state; unresolved work; useful resumption prompt | Praxis handoff/recovery. Composition alone is neither dispatch nor accepted ownership transfer. Preserve worker returns and coordinator integration. |
| `implement` | Consume the agreed target; TDD loop; review; focused completion | Praxis sequences the effort; engineering procedures own implementation; Tricritical and Versionkeeping retain review and Git responsibilities. |
| `implement-spec` | Dependency frontier; independent implementers; integration work; isolated worktrees; final review | Praxis coordinates; Rolecasting owns delegation, Versionkeeping worktrees/Git, and Tricritical review. Source merger/reset advice cannot replace their stronger controls. |
| `research` | Bounded question; grounded findings; primary evidence and retained research artifacts | Method ownership is unsettled; Praxis consumes findings and Rolecasting owns any dispatch. Do not turn “research uses a background agent” into an unsupported-route requirement. |
| `grilling` | Design tree; prerequisite-aware question frontier; environmental facts discovered by the agent; human decisions and actual answers; shared confirmation | Unsettled decision-development home used by Praxis and other owners. Keep reserved decisions human; do not force already-authorized routine choices through human pauses. |
| `grill-me` | Human entrypoint into the shared questioning method | Compatibility only if actual callers benefit; no second questioning implementation. |
| `grill-with-docs` | Questioning with active domain-model refinement and durable decisions | Same decision-development responsibility, with a clear domain-modeling seam. |
| `domain-modeling` | Canonical terms; contradictory usage; edge-case scenarios; code-versus-model checks; context maps; sparing ADRs | Unsettled model/requirements responsibility. Respect Provingkit’s `CONTEXT.md` convention rather than mechanically renaming it to the source’s glossary filenames. |
| `to-spec` | Synthesize settled requirements, interfaces, behavior, and acceptance seams into a durable specification | Unsettled requirements responsibility; Praxis owns sequencing and authority, not all specification content. |
| `to-questionnaire` | Recipient knowledge gaps; answerable questions; context and response structure | Decision-development method plus Proseweaving’s human prose. Delivery and any promised deadlines need their own authority and evidence. |
| `setup-matt-pocock-skills` | Discover repository tracker/domain policy; seed only missing conventions; label mappings; explicit setup choices | Unsettled repository-configuration method. Praxis consumes the policy; configuration and host bindings stay with their owners. Seed templates are not existing repository policy. |
| `wizard` | Prepare unavoidable human actions; capture useful results; idempotent setup assistance; return contract | Praxis owns the human hold and resumption; setup/control specialists own execution. Its shell template needs a separate source/security assessment before reuse. |

### Engineering, verification, and publication

| Source skill | Contributions to carry into the assessment | Proposed home and boundary |
| --- | --- | --- |
| `codebase-design` | Deep modules; interface cost and invariants; seams/adapters; locality; deletion test; alternative designs | Unsettled engineering-method home. Assess rules such as the two-adapter heuristic against actual needs rather than import them as universal law. |
| `improve-codebase-architecture` | Reconnaissance; specific design candidates; visual comparison; alternative designs; selecting a bounded improvement | Same engineering responsibility; Rolecasting owns any workers and domain/decision procedures own unresolved choices. Preserve useful checks without requiring a broad report for a narrow review. |
| `tdd` | Behavior-first tests; red–green learning loop; public-interface verification; independently expected results; boundary mocking; testability seams | Unsettled engineering responsibility. Preserve the prior Superpowers migration’s added failure-provenance rule and distinguish harness behavior evaluation from application unit tests. |
| `diagnosing-bugs` | Reproduce the exact symptom; minimize; rank hypotheses; instrument; prove the diagnostic change occurred; regress the fix; remove temporary instrumentation | Same engineering responsibility, with safe execution and redaction. Adapt rigid ordering to the authorized observation surface and incident controls. |
| `prototype` | Question-bound experiments; logic versus UI branches; domain-language examples; realistic surrounding UI; primary artifacts; separation from production delivery | Engineering experimentation with appropriate UI/design specialists. Prototype inspection cannot qualify lifted logic or excuse production tests. |
| `code-review` | Independent standards/specification perspectives; evidence-grounded critique; design heuristics | Tricritical is the candidate owner for applicable contributions, with its existing adjudication and review-loop contract preserved. Current installed presence and historical side-by-side disposition are not retirement. |
| `pr` | Reviewer-oriented explanation; smallest useful visual; before/after evidence; tests, blast radius, and reversibility | Mergecraft’s existing PR writers/publisher, using Proseweaving where appropriate. Preserve the additional Humanlayer `show-me` attribution recorded in `CREDITS.md`; the source describes copied material, not a runtime skill dependency. |

### Agent authoring, human writing, and learning

| Source skill | Contributions to carry into the assessment | Proposed home and boundary |
| --- | --- | --- |
| `writing-for-agents` | Actionable instructions; trigger discovery; progressive disclosure; local source ownership; completion criteria; pruning no-ops; skill mechanics | Unsettled agent-equipment authoring home, with actual honing/capture/skill-creator callers. Proseweaving’s human-writing contract is not automatically this owner. |
| `retro` | Evidence from the completed work; deterministic checks versus judgment instructions; useful navigation; corrections to authoring method | Same authoring/improvement responsibility, consuming `writing-for-agents` before judging instruction quality. Do not authorize blanket instruction edits or memory writes. |
| `wait-what` | Repair an explanation using plain language and shared domain vocabulary | Proseweaving candidate contribution, subject to a focused gap comparison; not evidence of a missing whole plugin. |
| `teach` | Learning goals; source resources; learning records; active recall and practice; durable learner context | Learning-method ownership/applicability remains open. Its four format references stay in the inventory; non-engineering material is not automatically excluded. |

### In-progress and misc material

These are source inputs, not selected installed capabilities. Source maturity and upstream maintenance policy affect confidence, not whether a useful contribution gets considered.

| Source skill | Contributions to carry into the assessment | Proposed home and boundary |
| --- | --- | --- |
| `chief-of-staff` | Strategic versus tactical work; useful context pointers; feedback into the working environment | Praxis and agent-authoring candidates. Do not inherit blanket delegation or environment-improvement on every message. |
| `claude-handoff` | Packet composition plus a named fresh-session launch | Praxis composition/recovery and a separately qualified Rolecasting route. Source instructions are not evidence that the launch surface is available. |
| `loop-me` | Distinguish events from schedules; prepare as much as possible before a genuine human checkpoint; avoid unnecessary AI work | Praxis continuation/human-hold assessment. This source already contains autonomy-oriented ideas; the migration should not caricature every Matt contribution as manual-only. |
| `setup-ts-deep-modules` | Structural enforcement of module boundaries; dependency-cruiser configuration; negative and restored checks | Engineering-method specialization. Preserve the validation technique without making its TypeScript tooling mandatory everywhere. |
| `writing-beats` | Plan the sequence and purpose of a piece before drafting | Proseweaving candidate; adapt interaction cadence to the actual request. |
| `writing-fragments` | Ground a draft in source fragments and build it incrementally | Proseweaving candidate; no automatic per-fragment approval requirement. |
| `writing-shape` | Establish the argument and document shape before polishing prose | Proseweaving candidate; preserve useful method without a second competing writer. |
| `git-guardrails-claude-code` | Intended guard behavior and explicit dangerous-operation cases | Versionkeeping/security assessment input. The frozen helper is not a qualified safety boundary and must not replace current Git controls. |
| `migrate-to-shoehorn` | Typed partial-fixture migration technique | Engineering specialization; applicability remains open, with no universal package dependency. |
| `scaffold-exercises` | Exercise structure and learner progression | Learning-method assessment; retain until applicability is decided. |
| `setup-pre-commit` | Inspect the project’s checks and tools, then configure an appropriate local check path | Repository-engineering method plus Versionkeeping’s Git boundary. Do not inherit staging-all behavior or a particular JavaScript hook stack as a default. |

## Dependencies are wider than skill calls

The following are source-level or maintained-caller relationships. They do not claim that every branch ran in a native session.

| Relationship | Evidence and classification | Migration consequence |
| --- | --- | --- |
| `grill-me` invokes `grilling`; `grill-with-docs` combines it with `domain-modeling` | Current source entrypoints; reusable method dependencies | A replacement must preserve the shared method and model seam, not only rename wrappers. |
| Wayfinder and triage use questioning/domain work; Wayfinder uses research/prototyping | Current source entrypoints; optional workflow composition | Keep independent direct-intake support. A workflow may retain these external methods until its own selected replacements are ready. |
| `implement`/`implement-spec` use TDD and review; TDD and architecture work use design principles | Current source entrypoints and TDD resources; development procedure dependencies | Replacing a coordinator does not retire its engineering method dependencies. |
| `retro` judges and updates instructions using `writing-for-agents` | Current source plus `.out-of-scope/lazy-load-writing-for-agents.md`; development aid | Authoring standards must be available before assessment, not loaded only at write time. |
| Dotfiles standing routing names grilling, domain modeling, durable requirements, TDD, architecture, and diagnosis | `home/dot_codex/private_AGENTS.md.tmpl` at the dotfiles baseline; maintained caller instructions | Actual routing surface to migrate. It still includes historical `to-prd` and `systematic-debugging` names; a text replacement alone cannot establish a working route. |
| Honing and procedure capture depend on Matt methods | `home/dot_agents/skills/honing-agent-facing-docs/SKILL.md`, `honing-human-facing-docs/SKILL.md`, and `capturing-agent-procedures/SKILL.md`; authoring/development dependencies | `writing-for-agents` and its skill mechanics, plus grilling, support the machinery that will build their replacements. Keep that bridge until the replacement is independently reviewed and usable. |
| Narrow code tightening consumes architecture vocabulary | `home/dot_agents/skills/tightening-code-for-review/SKILL.md`; development/review aid | Preserve the narrower caller contract; do not accidentally launch a broad architecture workflow. |
| Provingkit repository instructions refer to tracker and domain workflows | `AGENTS.md` and `docs/agents/`; repository operating conventions | Reconcile canonical project language and actual tracker policy separately from source seed templates. |
| Earlier Superpowers retirements select Matt diagnosis, TDD, and agent writing | [Prior disposition research](2026-08-23-source-skill-disposition-and-release-refresh.md) and `release/source-skill-disposition/disposition-ledger.json`; historical decision with continuing dependency implications | Carry those inherited obligations into each replacement’s evidence, rather than treating the Matt source as an isolated install. |
| Versionkeeping contains a maintained `resolving-merge-conflicts` derivative | Current owner skill and prior disposition research; already-absorbed contribution | Preserve attribution and compare the historical source contribution despite its absence from the current source tree. The prior research uses `84fdeffd12f2ee307994d1eb6feb48173b6e0502` as a conservative baseline, not a recovered exact import receipt. |

A bounded name search in Provingkit’s canonical skill instructions did not find the selected unambiguous Matt names used in that search. That does not establish zero deployed dependencies: generic names such as `pr`, `handoff`, and `code-review`, unnamed borrowed methods, transitive resources, and external consumers need semantic inspection in the relevant slice. No usage-frequency telemetry or cost comparison was collected; priority below is an inference from observed callers, this conversation’s friction, and owner readiness.

The source repository also contributes nine repository-convention files, nine scope/rejection records, three distribution helpers, six automation files, documentation, and change history. Their useful relationships belong in the assessment: hard versus optional setup requirements, one source for shared references, explicit invocation metadata, synchronized manifest selection, and recorded reasons for rejected requests. Its policies refusing native question tools, recursion guards, new skills, or harness-specific branches do not become Provingkit policy. Source history explains intent; the accepted Provingkit contract decides applicability.

## Preserving useful material without preserving the old stack

For each selected workflow slice, the contribution record should identify the exact source passage/resource and any further attribution, the required behavior or principle, the receiving owner, the adaptation or reasoned exclusion, affected callers, evidence, and cutover state. A current-source file can contribute to more than one owner. A proposed owner is not a final disposition, and “already have something similar” is not equivalence evidence.

The MIT license is present in the source inventory. Retain applicable notices and the source’s further credits when material is carried over. External links and package recommendations are research leads, not automatically approved dependencies. Artifact Customs can own admission/lifecycle checks for a selected third-party component; it does not thereby own all engineering or agent-authoring methods.

Keep the current source disposition ledger unchanged until the owning delivery work reconciles it with the accepted strategy. In particular, its historical side-by-side `code-review` ruling and its maintained merge-conflict derivative classification are records to reconcile, not proof that the newly accepted whole-stack exit has already happened. After an adopted contribution’s external dependency is actually retired, later Matt changes become optional research inputs as decided; the relevant refresh/disposition contracts must be updated explicitly at that boundary.

## Proposed delivery sequence

I recommend the following first workflow slice: preserve and recover one authorized effort across a context boundary, using direct input, a complete handoff packet, explicit unresolved obligations, and verified receiver consumption. It addresses an observed workflow friction, has an accepted Praxis responsibility, and can be scoped without first designing the entire engineering stack. This is a recommendation for the adoption decision, not authorization to implement it now.

| Candidate first slice | Why it helps | Remaining cost or gate |
| --- | --- | --- |
| **Handoff composition and recovery, within one bounded generic effort** | Makes an existing workflow agent-invocable within authority; exercises preservation of decisions, obligations, and completion responsibility | Needs the compatible Praxis source seam, actual consumer, operating limits, and separate harness evidence. Composition can be prepared independently; live dispatch/return cannot be claimed without its route. |
| Agent-procedure authoring and improvement | High dependency leverage: the migration’s honing/capture path itself uses Matt writing and grilling | New ownership boundary is unsettled; a broad authoring system would delay the first practical replacement. Keep the current authoring bridge meanwhile and develop this boundary in parallel. |
| Engineering diagnosis/design/TDD | Removes heavily routed and inherited dependencies | Largest semantic surface, specialized workloads, and unresolved owner boundary. Prepare its contract in parallel; do not make it a blanket prerequisite for a handoff slice. |
| Existing-owner contribution reconciliation | Tricritical, Mergecraft, Versionkeeping, and Proseweaving already own related behavior | Useful independent gap checks, but current similarity does not prove coverage or retire a source. Avoid adding no-op instructions merely to claim an import. |

The first slice’s end-to-end acceptance should cover the packet’s source fidelity, preserved grants and human holds, unknown effects, outstanding obligations, the receiver locating and loading the reviewed procedure, complete relevant result consumption, and truthful parent completion. Positive/negative discovery and separate route evidence remain required. A delivered packet, notification, or worker completion is not the resumed parent’s completion. No new scheduling, shared monitor, or cross-chat messaging authority follows from this slice.

Independent preparation can proceed for the authoring, decision/model/requirements, engineering, human-writing, and existing-specialist contribution families. Join only where an actual consumer requires another owner’s reviewed output. Do not dispatch speculative work or assign an owner merely because the source table names a likely home.

### Existing work to consume, not duplicate

- [Migrate Matt Pocock skill names and file references after plugin replacement](https://github.com/nisavid/provingkit/issues/477) supplies the continuity naming/file audit: `to-prd` to `to-spec`; `to-plan`/`to-issues` to `to-tickets`; `writing-great-skills` to `writing-for-agents`; `decision-mapping` to `wayfinder`; `diagnose` to `diagnosing-bugs`; and source glossary-file changes. Keep its owner and deployment prerequisites. The long-term replacement does not make currently needed caller repairs disappear, nor justify a blind global rename.
- [Deliver workflow-ownership migration into Praxis](https://github.com/nisavid/provingkit/issues/607) owns its already-scoped workflow migration. Feed the relevant contribution/caller findings into that work without turning it into ownership of the entire Matt-origin program.
- [Sequence Praxis’s adoption and predecessor-compatible integration](https://github.com/nisavid/provingkit/issues/161) decides the executable order and final handoff. It retains the predecessor’s reserved manifest, topology, content-lock, and shared integration seams. Prepare disjoint work now; hold only the steps that consume unavailable published or qualified output.

### Cutover and rollback boundary

Cut over one contribution, selected consumer set, and harness route at a time. Bind its reviewed source revision, current behavior evidence, discovery name, installation/projection, and caller record. Keep one active provider for a selected name in that target environment; a retained rollback copy is not a competing discovered provider. Preserve useful compatibility entries only when they delegate to the same maintained implementation.

New sessions may use the verified replacement. Existing efforts stay on their recorded revision until closeout or an explicit reconciled handoff that preserves identities, ownership, unresolved effects, and obligations. A rollback restores the known supported provider and reconciles in-flight work; it cannot undo external actions by simply switching instruction files. Retirement waits for migrated callers and current required evidence, not for installation or a successful happy-path invocation alone.

## Decisions still needed

1. Define the receiving boundary for agent-equipment authoring and improvement, including the existing honing/capture/skill-creator relationships. Decide whether a focused new plugin is warranted; do not assume Proseweaving or Praxis absorbs it.
2. Define the engineering-method and decision/model/requirements boundaries. They may share resources or ultimately an owner, but the source’s current folder layout is not sufficient reason to combine them.
3. Confirm or change the first bounded handoff/recovery slice through the adoption decision, with its actual consumer and compatible predecessor seam. No final public skill name or compatibility alias is selected here.
4. Assess learning/exercise specializations and any consequential exclusion when their contribution-level review is ready. Lack of observed use in this bounded search is not grounds to discard them.

All inventory entries remain accounted for while these choices are open. Current skills continue to supply unmigrated behavior; implementation, qualification, targeted installation, consumer cutover, and retirement remain later work with their owners.
