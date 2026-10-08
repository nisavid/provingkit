# Repository initialization and foreign intake

Existing equipment covers fork discovery, guarded fork configuration, explicit repository setup, stakeholder decisions, and domain modeling. The distinct gap is a procedure that selects and composes those owners across greenfield, foreign, mirror, modified-fork, partial, and no-op cases while preserving existing policy and source ownership.

This research answers [#472](https://github.com/nisavid/provingkit/issues/472). [#473](https://github.com/nisavid/provingkit/issues/473) retains the source, scope, invocation, and adoption decisions. It does not widen the five-workflow [repository-configuration alpha](https://github.com/nisavid/provingkit/issues/374) or establish a new implementation, installation, successful sync, or client qualification.

## Inspected sources and coverage

On 2026-10-08, I recovered source ownership from the installed Fork Ops adapter manifest, Matt Pocock skill-manager records, and maintained dotfiles source. I fetched the following files through GitHub at immutable revisions, decoded their content, and compared complete bytes with installed copies. Every listed comparison matched. These are file bindings, not whole-plugin integrity or runtime evidence.

| Equipment | Maintained revision and source | Coverage and limit |
| --- | --- | --- |
| `onboarding-forks-for-agent-maintenance` | [Dotfiles `3feb1c44317338dcc8b63fce38d6db58f592abba`][onboarding] | Discovers upstreams, baseline, intentional divergences, generated-source ownership, and validation gates; creates minimal fork-local policy. Actual sync stays with `syncing-forks-with-upstream`. |
| `fork-ops` | [Fork Ops `546d9ecaf10d3ef9ee08f6fcca1301831f7d47b4`][fork-ops] | Reads fork-local authority, validates config, and assesses migration. Its [operation guide][fork-guide] documents guarded initial config creation and preserved retained authority; broad sync, publication closeout, equipment edits, and source-material removal remain outside that foundation. |
| `setup-matt-pocock-skills` | [Matt Pocock `f3fc5632f401156837ee3872f14fe33ccf1024ea`][setup] | Discovers existing setup, presents decisions and drafts, and writes confirmed tracker, triage, and domain guidance. It remains explicitly human invoked. It does not define complete reconcile, no-op, or recovery behavior. |
| `grilling` | [Same Matt Pocock revision][grilling] | Finds facts before asking, works the available decision frontier, waits for answers, and confirms shared understanding before execution. |
| `domain-modeling` | [Same Matt Pocock revision][domain] | Changes terminology and ADRs when needed; reading vocabulary alone is ordinary consumption. Its current names are `GLOSSARY.md` and `GLOSSARY-MAP.md`. |

Complete-file SHA-256 bindings for the five Skill bodies, in table order, are:

```text
onboarding: 30faaf6311d130e5edf93caf82282d9d0078472dfc2d30a7ebe6bf7912334e8b
fork-ops:   7fc508164ce509c103868ee06713268a3261d94f8412f667684ff44ad9e30de4
setup:      f148858ffb7f63c03c06fca06e6fdb1d91a35c6b293244b8fdfacd5f4cc028c4
grilling:   befdff1e27a1dfe2a294d5871169ac1afe16d983911daa4f32627514a48c1e15
domain:     7b925d7b1e341a2eeae33ad68a8a8c0ab889a38ddd22a7598e4c240e5a7556a3
```

The Fork Ops operation guide also matched at `f3e06ec8b0b646d8e4d9302f1056a622e03165c5906958a084029d774d41753a`. Its documented config path can create `.agents` alone and report `applied_unverified`; a later call binds that directory before creating config. Failed post-create verification preserves an extant target for review. Intake must reconcile observed effects before retrying, without guessing rollback.

## Existing producers remain the owners

[Agents #124](https://github.com/nisavid/agents/issues/124) owns the setup-successor decision map and convergence route. [#130](https://github.com/nisavid/agents/issues/130) owns preservation of repository additions during canonical-section refresh; its marker-delimited approach is a recommendation, not a decision. [#132](https://github.com/nisavid/agents/issues/132) owns shared wording and consumes the autonomy-declaration producer. All three were open with no returned comments when read. Intake should consume their reviewed results rather than invent another successor, section-merging algorithm, or autonomy template. Shared-text ownership, package home, and retirement also remain with that map's existing children.

The [current GitHub setup seed][github-seed] has already corrected the older map's issue-read, ticket-fetch, and external-PR field examples. Its list example still omits explicit `--limit`, frontier scoping remains prose, and its Resolve example closes the child before updating the map. The older defect inventory is therefore not entirely current. Route useful corrections and refresh requirements to the existing producer; these source differences were not exercised as runtime tests.

[Provingkit #477](https://github.com/nisavid/provingkit/issues/477) owns skill-name and domain-file migration after updated Matt Pocock plugin deployment. It remains an explicit dependency, not a global replacement authorized here. Provingkit's inspected [domain guidance][provingkit-domain] still uses `CONTEXT.md`; the current Matt source uses `GLOSSARY.md`. Preserve each repository's current contract until its authorized migration lands.

At inspected Provingkit commit `fcb671c79af39d41ca687dc533153bc08ae4b139`, the proposed `configuring-repositories` Skill was absent. Its [source/installation contract][alpha-source] and [qualification contract][alpha-qualification] own GitHub creation, assessment, defaults, focused changes, and CI hardening. Their immutable candidate, client, installation, recovery, and behavioral obligations remain intact; this observation says nothing about another implementation branch.

## Intake cases and preservation

Upstream file-shape observations supplied to the case investigation distinguish [TypeSafe `65a39f393687675ce170e6094757de20370365b9`](https://github.com/typesafe-ai/skills/tree/65a39f393687675ce170e6094757de20370365b9), with neither root instruction file, from [Matt Pocock `f3fc5632f401156837ee3872f14fe33ccf1024ea`](https://github.com/mattpocock/skills/tree/f3fc5632f401156837ee3872f14fe33ccf1024ea), with regular `CLAUDE.md` and an `AGENTS.md` symlink to it. Under the operator's stated convention, the former uses AGENTS only; the latter preserves its existing file/link contract. This is not a universal foreign-repository rule.

The separate local case reads occurred during active owner work and were hashed without establishing an immutable local commit. They observed no root instructions or setup docs in TypeSafe, while the Matt fork had local tracker, distribution, invocation, and Fork Ops guidance. Its local domain contract used `GLOSSARY.md` and `.agents/adr/`; its upstream track was manual and `sync_eligible = false`. These observations are not attributed to either immutable upstream revision. Existing setup can be complete for inspection while sync remains intentionally restricted.

| Case | Reusable route | Decision or preservation requirement |
| --- | --- | --- |
| Greenfield | Discover checkout, project, owner, existing files, and authorized outcome; compose the existing GitHub and setup owners where applicable. | Purpose, destination, nondefault policy, and application authority remain decisions when unsupplied. Apply the operator file convention only within its scope. |
| Foreign repository with policy | Recover actual instruction/link shape, tracker, domain layout, maintainer policy, and generated-source ownership. | Preserve inherited policy and authorized local additions. File absence does not erase product ownership or authorize house-policy replacement. |
| Pure-mirror fork | Establish intended fidelity and actual divergence separately from forge fork status or package metadata. | New instructions/config themselves create divergence. Decide whether they are permitted and where operating guidance belongs; neither specimen was classified as a pure mirror. |
| Modified fork | Reuse onboarding and Fork Ops assessment/preflight; retain reviewed source authority and explicit gates. | Config creation does not qualify sync or permit equipment replacement. Actual sync retains its existing owner. |
| Already initialized no-op | Verify current instructions, references, policy, and separately applicable remote state against the requested result. | Preserve sufficient existing content. A no-op still invokes intake and needs observable sufficiency/freshness evidence; it is not negative discovery. |

Partial setup needs component-level observations: a pointer may lack its docs, docs may lack discovery, or restricted config may be deliberate. Preserve completed authorized work and distinguish interruption from staging before recovery. Conflicts include an unexpected local CLAUDE despite upstream absence, two independent instruction files, duplicate blocks, changed symlink targets, and contradictory tracker/domain/sync policy. The AGENTS-only convention does not authorize deleting an existing local file. Preserve bytes and ownership, then use `grilling` for unresolved consequential choices. Missing authority or a control surface holds the dependent operation while independent discovery continues.

## Composition and the design frontier

I recommend a focused intake Skill owning discovery, case selection, preservation, decision routing, and composed-result evidence. It consumes the existing configuration, fork, and setup procedures rather than duplicating their writers, templates, sync implementation, or Git publication mechanics.

A provisional source option is `nisavid/dotfiles` beside maintained fork onboarding, supported by its existing global-Skill ownership route. The operator's AGENTS-only convention is a separate input; this research did not establish that dotfiles already implements it. A portable released-plugin option requires a named maintained home and client claim. Neither option is selected, and intake's placement must not indirectly decide the setup successor's separate home.

The next decision frontier is:

1. **First outcome:** discovery/orchestration only, or separately authorized bounded local application, with observable completion for each slice.
2. **Intake invocation:** human-only, or model invocation within an active authorized session. This remains open. The current setup Skill's human-only contract forbids silent setup invocation, including from another Skill; it does not decide future intake authority.
3. **Source and adoption:** choose maintained home, target clients, supported projections, and recovery owner.
4. **Preservation and dependencies:** define mirror fidelity, foreign-policy reconciliation, and how intake resumes after explicit setup or consumes a reviewed successor.
5. **Acceptance evidence:** select success, conflict, no-op, stale-input, unavailable-authority/control-surface, and partial-effect cases across the supported categories.

## Capture and evidence limits

The eventual producer must capture its trigger, inputs, decision branches, owners, completion criteria, and minimal discovery pointers in maintained source. Consumers identify the reviewed revision they load and return corrections to its owner. Managed caches remain immutable; [managed-skill ownership][managed] and [procedure capture][capture] govern corrections and adoption.

Qualification must distinguish ordinary-language positive discovery from nearby negatives, and source review from real application. Every selected review focus and behavior evaluation needs a current clean result on the same final candidate. Bind authorized publication/projections, preserve prior provider identities for recovery, and verify useful fresh invocation on the selected clients. Material input changes invalidate affected evidence.

This research ran no Fork Ops health/application, setup, sync, installation, client invocation, or new-Skill evaluation. Local files, registration, and matched instructions do not establish capability. TypeSafe's successful, deeply validated sync remains a prerequisite for the Matt owner reusing that implementation; ongoing local-test reports do not satisfy it. Independent intake research and the existing GitHub alpha continue. Any later validated-procedure prerequisite belongs only on the dependent slice, without creating cycles or transferring either repository owner's work.

[onboarding]: https://github.com/nisavid/dotfiles/blob/3feb1c44317338dcc8b63fce38d6db58f592abba/home/dot_agents/skills/onboarding-forks-for-agent-maintenance/SKILL.md
[fork-ops]: https://github.com/nisavid/fork-ops/blob/546d9ecaf10d3ef9ee08f6fcca1301831f7d47b4/plugins/fork-ops/skills/fork-ops/SKILL.md
[fork-guide]: https://github.com/nisavid/fork-ops/blob/546d9ecaf10d3ef9ee08f6fcca1301831f7d47b4/plugins/fork-ops/docs/operation-guide.md
[setup]: https://github.com/mattpocock/skills/blob/f3fc5632f401156837ee3872f14fe33ccf1024ea/skills/engineering/setup-matt-pocock-skills/SKILL.md
[grilling]: https://github.com/mattpocock/skills/blob/f3fc5632f401156837ee3872f14fe33ccf1024ea/skills/productivity/grilling/SKILL.md
[domain]: https://github.com/mattpocock/skills/blob/f3fc5632f401156837ee3872f14fe33ccf1024ea/skills/engineering/domain-modeling/SKILL.md
[github-seed]: https://github.com/mattpocock/skills/blob/f3fc5632f401156837ee3872f14fe33ccf1024ea/skills/engineering/setup-matt-pocock-skills/issue-tracker-github.md
[provingkit-domain]: https://github.com/nisavid/provingkit/blob/fcb671c79af39d41ca687dc533153bc08ae4b139/docs/agents/domain.md
[alpha-source]: https://github.com/nisavid/provingkit/blob/fcb671c79af39d41ca687dc533153bc08ae4b139/docs/superpowers/specs/2026-10-06-repository-configuration-alpha/source-and-installation.md
[alpha-qualification]: https://github.com/nisavid/provingkit/blob/fcb671c79af39d41ca687dc533153bc08ae4b139/docs/superpowers/specs/2026-10-06-repository-configuration-alpha/qualification.md
[managed]: https://github.com/nisavid/dotfiles/blob/3feb1c44317338dcc8b63fce38d6db58f592abba/home/dot_agents/skills/extending-managed-skills/SKILL.md
[capture]: https://github.com/nisavid/dotfiles/blob/3feb1c44317338dcc8b63fce38d6db58f592abba/home/dot_agents/skills/capturing-agent-procedures/SKILL.md
