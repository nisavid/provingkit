# Mergecraft relation entry points and rollout inventory

Mergecraft has established Issue and PR body writers, guarded PR publication,
and merge coordination. It needs an explicit owner for relation maintenance,
an authorized Issue-body update route, and operation-specific native-link
controls before those existing routes can maintain the relations requested in
[Reliable Issue–PR Development relations and historical repair](https://github.com/nisavid/provingkit/issues/85). The selected repair
scope contains 24 repositories, 961 Issues, and 670 PRs. A future equipment
revision also needs a new deployment candidate; the published preview and its
active Linux rollout cover an earlier, fixed candidate.

## Evidence boundary

This report answers [Research Mergecraft relation entry points and rollout inventory](https://github.com/nisavid/provingkit/issues/87).
I inspected canonical source at
[`147e1ddfc969b5119001488ce1556627d3b2449b`](https://github.com/nisavid/provingkit/commit/147e1ddfc969b5119001488ce1556627d3b2449b),
which matched the live GitHub `main` commit during this investigation on
2026-09-17 UTC. Source links below are repository-relative and describe that
revision. Repository counts, issue state, and the limited cache observations
are dated observations that consumers must refresh before dependent action.

I used `research`, `capturing-agent-procedures`, and
`extending-managed-skills`. The reusable procedure belongs in canonical
Provingkit equipment, with invocation pointers in its consuming workflows.
Installed managed copies are evidence for discovery and deployment, not the
source to edit. This investigation changed only this report; it did not
implement equipment, change tracker objects or settings, install anything, or
repair historical bodies and relations.

GitHub platform semantics belong to
[Research GitHub Development link and automatic closure semantics](https://github.com/nisavid/provingkit/issues/86). The operation
gaps below do not settle native-link cardinality, merge-triggered closure,
historical link mutability, or the eventual choice of API and browser controls.

## Existing ownership and the missing procedure

The [domain glossary](../../../CONTEXT.md) separates a semantic writer's exact
content from an actuator's authorized state change.
[Mergecraft's topology](../../../plugins/mergecraft/topology.json) is the sole
operation-ownership map. I enumerated all 47 operations, including the two
read-only Issue operations, `github:issue-orientation` and
`github:issue-summary`. None owns Issue-body mutation or adding or removing a
native Issue–PR Development relation.

| Surface | Existing owner and verified contract | Relation increment it could consume |
| --- | --- | --- |
| PR body | [writing-reviewable-pr-descriptions](../../../plugins/mergecraft/skills/writing-reviewable-pr-descriptions/SKILL.md) owns the complete validated title/body pair within the authorized text surface. | A relation ledger and its evidence must enter this writer's content contract; a coordinator must preserve the existing title, authored spans, navigation, and bot-tail rules. |
| Issue body | [writing-github-issue-and-pr-markdown](../../../plugins/mergecraft/skills/writing-github-issue-and-pr-markdown/SKILL.md) owns exact GFM bytes and explicit retain/replace/remove dispositions. It expressly grants no Issue actuation or lifecycle authority. | It can render authorized ledger spans. The caller still needs an Issue-specific semantic and mutation contract. |
| Stored PR body and PR creation | [publishing-reviewable-prs](../../../plugins/mergecraft/skills/publishing-reviewable-prs/SKILL.md) invokes the PR writer, preflights the live object, mutates once, rereads, and stores publication evidence. | Relation text should use this owner. Native-link changes cannot be inferred from its PR text authority. |
| Merge outcome | [getting-prs-merged](../../../plugins/mergecraft/skills/getting-prs-merged/SKILL.md) coordinates current evidence and delegates the merge write. PR text and deployment remain outside its ownership. | It is the existing boundary at which any chosen policy about merge consequences needs an explicit check or handoff. It does not currently own Issue completion adjudication or relation repair. |
| Resume, readiness, and stacked work | [resuming-reviewed-prs](../../../plugins/mergecraft/skills/resuming-reviewed-prs/SKILL.md), [getting-prs-ready-for-review](../../../plugins/mergecraft/skills/getting-prs-ready-for-review/SKILL.md), [graphite](../../../plugins/mergecraft/skills/graphite/SKILL.md), and [stacking-pr-fixups](../../../plugins/mergecraft/skills/stacking-pr-fixups/SKILL.md) route work among the established lifecycle owners. | Each supported entry route needs a deliberate invocation path if it can create or materially change relation evidence. A new skill's presence alone does not establish discovery through these callers. |

The PR writer's
[body contract, “Hard Rules And Acceptance”](../../../plugins/mergecraft/skills/writing-reviewable-pr-descriptions/references/body-contract.md#hard-rules-and-acceptance)
forbids inferring Issue closure from a PR number, branch name, or nearby
identifier. It preserves Issue links and closure semantics supplied by verified
source or the live body. That is a preservation rule, not a procedure for
discovering every supported association, choosing closure permission, updating
both ledgers, or reconciling native Development state.

For a concrete live example, [PR #82](https://github.com/nisavid/provingkit/pull/82)
identifies its work for [Research invocation evidence and protected-evidence transport](https://github.com/nisavid/provingkit/issues/43)
in its Summary, while its `closingIssuesReferences` connection was empty when
read. This demonstrates that the visible association and that API field can
differ. It does not establish which other native relation surfaces exist, that
closure should be enabled, or that this open PR is safe to mutate.

The publisher's current contract also states that GitHub has no conditional
write for its text update and that its local publication lease cannot serialize
other machines, users, or bots. Any proposed multi-object procedure must account
for stale preimages, partial success, and concurrent edits; the existing
read-write-reread sequence does not make two ledgers and a native link atomic.

## Narrow discovery candidates

The following are proposed invocation boundaries for
[Choose Issue–PR relation maintenance and closure policy](https://github.com/nisavid/provingkit/issues/88), not newly installed
rules:

| Trigger candidate | Required boundary |
| --- | --- |
| Create an Issue or PR with evidence of a contribution relationship. | Bind repository-qualified entities and distinguish a proposed body from an authorized publication. PR identity is unavailable until creation assigns it. |
| Materially change an Issue's completion contract or a PR's contribution scope. | Reacquire the relevant relation evidence and change only authorized spans and links. A title-only or formatting edit should not silently become a historical repair. |
| Explicitly maintain or repair Issue–PR Development relations or their body ledgers. | Invoke the relation owner directly with a finite entity set and declared evidence, authority, and completion criteria. |
| Prepare a merge whose linked Issues may close under the selected platform and repository policy. | Verify the chosen closure policy through the merge owner and route any text or link mutation to its separate actuator. |

Negative discovery cases should include read-only relation inspection, a
chat-only proposal, comments or review replies, labels or reactions, ordinary
dependency and sub-issue work, unrelated body formatting, and a plain mention
with no supported contribution claim. Whether a particular “material update”
should invoke maintenance remains a policy decision. The procedure also needs
to distinguish its own ledger refresh from new contribution evidence so that
updating one endpoint does not create an endless cycle of reciprocal edits.

Existing trigger corpora establish the surrounding boundaries: the
[PR writer corpus](../../../evals/mergecraft/skills/writing-reviewable-pr-descriptions/trigger-evals.json)
distinguishes creation and body edits from read-only inspection, comments,
labels, base changes, and merge-only work; the
[portable Markdown writer corpus](../../../plugins/mergecraft/skills/writing-github-issue-and-pr-markdown/evals/trigger-evals.json)
distinguishes exact body authoring from posting unchanged text and lifecycle
actions. Neither corpus qualifies the proposed relation procedure. Positive
and negative discovery evidence must cover both direct invocation and each
selected caller.

## Validation and source ownership

The maintained surfaces are
[`plugins/mergecraft/`](../../../plugins/mergecraft/), its
[`topology.json`](../../../plugins/mergecraft/topology.json), and the support
artifacts named by its [README](../../../plugins/mergecraft/README.md).
The roster is closed by
[`scripts/validate_mergecraft.py`](../../../scripts/validate_mergecraft.py): a
new public skill needs its own `agents/openai.yaml`, entries in `PUBLIC_SKILLS`,
`EXPECTED_SKILL_FILES`, and `CODEX_PROMPTS`, topology ownership and calls, and
the matching generated README operation registry. Adding only a `SKILL.md`
would fail the current inventory and discovery checks.
The later implementation should use their existing owners and validators:

| Changed surface | Owning acceptance evidence |
| --- | --- |
| Skills, references, topology, and helper contracts | `python scripts/validate_mergecraft.py .`, the relevant `python -m unittest` suites in `tests/plugins/mergecraft/`, and `tests.test_validate_mergecraft`. |
| Relation behavior and discovery | New behavior and trigger cases alongside the relevant corpora under `evals/mergecraft/`; the portable writer's corpus is skill-local. Run the affected cases against frozen candidate bytes and retain actual executor and grader evidence. |
| Portable Markdown contract | Edit `plugins/mergecraft/skills/writing-github-issue-and-pr-markdown/references/authoring-contract.md`; regenerate its three writer projections only through `python scripts/validate_mergecraft.py . --write-markdown-projections`. The relation change may not need to alter this shared formatting contract. |
| Governed Mergecraft identity | Refresh valid candidate evidence before `python scripts/validate_mergecraft.py . --write-content-lock`, which writes `release/plugin-content-locks/mergecraft.json`. The projection-writing and lock-writing modes are separate. |
| `plugins/`, `release/`, or source-contribution dispositions | `python scripts/validate_source_skill_disposition.py .`; inspect `release/source-skill-disposition/disposition-ledger.json` and `release/source-skill-disposition/release-refresh-contract.json` for affected source contributions. A disposition does not grant installation or removal authority. |
| Every changed increment | `git diff --check`, current required review, and evidence tied to the final candidate and its relevant dependencies. |

The current
[source workflow](../../../.github/workflows/provingkit-source.yml)
runs `tests.test_validate_mergecraft`, `tests.test_feedback_response_evidence`,
the feedback acquisition and response unit suites, and
`scripts/validate_mergecraft.py . --source-stage`. Source-stage validation
deliberately skips the ordinary content lock, as the Mergecraft README
explains. A green source job is therefore not a claim that a new content lock,
behavior run, installation, or runtime invocation has been qualified.

The relation increment needs externally meaningful cases for supported
association evidence, closure permission, retained authored content, no-op
convergence, stale observations, concurrent edits, and partial or unknown
mutation outcomes. Cross-repository, fork, private, Issue-disabled, and
historical entities need explicit supported or unsupported results after
the platform research and relation and repair decisions settle their contracts. This report identifies
those evidence needs; it does not declare a test result for unimplemented work.

## Overlapping work

These issues were open during this investigation:

| Work | Shared surface and consequence |
| --- | --- |
| [Carry eval results in equipment PR bodies](https://github.com/nisavid/provingkit/issues/28) | PR writer and publisher contracts. Coordinate any PR ledger placement and body-validation changes with this existing producer. |
| [Gate Mergecraft ready and merge coordinators on eval receipts](https://github.com/nisavid/provingkit/issues/34) | Readiness and merge coordinators. Relation checks must preserve the separately owned receipt gates. |
| [Embed salient images in GitHub Issue and PR bodies and comments](https://github.com/nisavid/provingkit/issues/41) | Seven-field Markdown authoring and image preservation. Ledger edits must preserve still-current authored material, including images. |
| [Implement Mergecraft feedback response routing and correlation](https://github.com/nisavid/provingkit/issues/10) | The implementation is merged, but the live issue says rewritten executor and grader requests retained earlier responses and completion claims. It requires fresh runs and review of the changed candidate. Do not treat that existing evidence as proof of new candidate execution. Its PR conversation transport expressly grants no Issue-body or Issue-lifecycle authority. |
| [Roll out and verify the preview on Linux x86_64](https://github.com/nisavid/provingkit/issues/70) under [Provingkit preview rollout and evidence](https://github.com/nisavid/provingkit/issues/66) | The active worker exclusively owns that rollout's inventory, installation, enablement, runtime checks, and cleanup. A relation deployment must coordinate its candidate and change window with this owner. |

These are coordination boundaries, not newly imposed dependencies on every
issue. The coordinator should re-read their current claims and candidate
revisions before selecting overlapping edits or live actions.
Keep shared references and retained experiment dependencies outside the
relation change unless it deliberately includes their affected requalification.

## Hatchery deployment: procedure and observation

The reviewed public entry points are
[Linux installation preparation](../../preview/linux-installation.md) and
[pinned preview installation and update](../../preview/install-and-update.md).
They require a qualified target projection, the accepted exact root
`RECEIPT.json` bytes and digest, retained mode evidence, saved registration and
enablement state, and separate verification of discovery and fresh runtime
behavior. They explicitly distinguish source `main`, the target artifact, its
publication, the installed cache, and the loaded runtime.

The available documented preview is
[`preview-8acd0e2af1f4`](https://github.com/nisavid/provingkit/releases/tag/preview-8acd0e2af1f4),
qualified from source
`8acd0e2af1f4508a0e2358d8e01f6a3db7a78ce3`. Its supported targets are Agent
Plugins/Codex, Claude Code, and Cursor. All member manifests report `1.0.0`, so
that version string cannot identify the source or target bytes. Updating the
procedure does not change the fixed preview; it cannot deliver a future
relation implementation.

The live assignment in [Roll out and verify the preview on Linux x86_64](https://github.com/nisavid/provingkit/issues/70#issuecomment-5695907259)
names procedure revision `089e62e306734d66187d74e7122d8ad17f418714` separately
from the preview's qualified product source. It reserves live mutation for its
worker and requires coordination before editing either installation guide.
This investigation does not consume that worker's authority.

My live observation was narrower than rollout qualification: the current task
could read a cached Mergecraft manifest reporting `1.0.0`. Three sampled
`SKILL.md` files matched the inspected source: `writing-reviewable-pr-descriptions`,
`writing-github-issue-and-pr-markdown`, and `publishing-reviewable-prs`.
`getting-prs-merged` differed: its inspected source SHA-256 was
`c2188e2cb227cc3362adeda08123f2aef63413b5842e06e72989ddba7e8f712b`,
and its cached file SHA-256 was
`81b99ee2dabfa16c6f8cc31e091628d06a50062d6590a628af329566ad0ebb64`.
This partial byte comparison establishes neither whole-plugin provenance nor
the content selected by any fresh client session. I did not verify the active
manager registration, Codex app record, other client controls, or runtime
activation. The dated 2026-09-16 inventory in the preparation guide remains
documentary context rather than a current host inventory.

The later deployment consumer therefore needs the reviewed relation procedure
and immutable source revision, a newly qualified candidate and target identity,
a coordinated installation window, rollback evidence for the actual previous
installation, and discovery plus behavior evidence from the selected Hatchery
clients. The client matrix and replacement route remain decisions for the
deployment increment; they are not settled by the presence of a cache or an
earlier preview receipt.

## Selected repository inventory

The recorded choice in [Choose the active-repository scope and historical repair contract](https://github.com/nisavid/provingkit/issues/89#issuecomment-5720772902)
selects all 24 non-archived repositories owned by the account, including private
and test/qualification repositories, with the complete historical and current
Issue and PR corpus. This is an explicit scope choice; recency and saved-project
membership do not narrow it.

I queried GitHub's authenticated GraphQL API with owner affiliation, enumerated
all repository pages, and read per-repository `issues` and `pullRequests`
`totalCount` fields with state-specific totals. A second enumeration used pages
of 20, exhausted all three cursor pages, and confirmed 55 distinct owned
repositories: 31 archived and 24 selected. The selected set has 22 public
repositories and two private repositories whose names and individual metadata
are omitted here. All 24 returned `ADMIN` for the authenticated operator; none
was disabled, six were forks, and one was empty. These permission observations
do not grant an agent permission to mutate arbitrary fields or bypass branch
and operation controls.

The count snapshot was complete by **2026-09-17 20:28:56 UTC**. It excludes
subsequent tracker changes made during this investigation, including the
qualification ticket created at 20:35:34 UTC. Counts are repository-contained objects, not every PR authored by the account
against other owners' repositories. Issue totals exclude PRs. PR “closed”
below means closed without merge; merged PRs occupy their own column. Last push
is GitHub's `pushedAt` observation, not proof of recent Issue activity or a
maintained project.

| Public repository | Fork | Issues enabled | Last push, UTC date | Issues: open / closed | PRs: open / merged / closed |
| --- | --- | --- | --- | --- | --- |
| [agent-armory](https://github.com/nisavid/agent-armory) | No | Yes | 2026-06-16 | 53 / 74 | 0 / 86 / 3 |
| [agents](https://github.com/nisavid/agents) | No | Yes | 2026-09-11 | 20 / 35 | 0 / 38 / 6 |
| [arch-pkgs](https://github.com/nisavid/arch-pkgs) | No | Yes | 2026-08-19 | 28 / 33 | 2 / 20 / 0 |
| [arch-strix-halo-pkgs](https://github.com/nisavid/arch-strix-halo-pkgs) | No | Yes | 2026-08-21 | 37 / 17 | 2 / 73 / 4 |
| [astrocommunity](https://github.com/nisavid/astrocommunity) | Yes | No | 2024-04-05 | 0 / 0 | 0 / 0 / 0 |
| [astronvim-config](https://github.com/nisavid/astronvim-config) | No | No | 2025-03-24 | 0 / 0 | 0 / 0 / 0 |
| [codiquary](https://github.com/nisavid/codiquary) | No | Yes | 2026-09-17 | 10 / 19 | 4 / 6 / 3 |
| [computer-use-linux](https://github.com/nisavid/computer-use-linux) | Yes | Yes | 2026-09-16 | 0 / 8 | 2 / 1 / 0 |
| [cqmgr](https://github.com/nisavid/cqmgr) | No | Yes | 2026-08-31 | 4 / 54 | 3 / 45 / 6 |
| [dotfiles](https://github.com/nisavid/dotfiles) | No | Yes | 2026-09-17 | 94 / 93 | 7 / 95 / 10 |
| [dummy-repo](https://github.com/nisavid/dummy-repo) | No | Yes | 2016-09-15 | 0 / 0 | 1 / 0 / 1 |
| [fork-ops](https://github.com/nisavid/fork-ops) | No | Yes | 2026-08-16 | 23 / 34 | 0 / 33 / 4 |
| [lemonade](https://github.com/nisavid/lemonade) | Yes | Yes | 2026-09-17 | 67 / 28 | 3 / 47 / 4 |
| [mastic](https://github.com/nisavid/mastic) | No | Yes | 2026-09-08 | 24 / 19 | 8 / 38 / 18 |
| [nisavid.io](https://github.com/nisavid/nisavid.io) | No | Yes | 2026-02-20 | 0 / 0 | 1 / 1 / 1 |
| [oai-plugins](https://github.com/nisavid/oai-plugins) | Yes | No | 2026-08-18 | 0 / 0 | 1 / 0 / 0 |
| [provingkit](https://github.com/nisavid/provingkit) | No | Yes | 2026-09-17 | 29 / 33 | 3 / 21 / 3 |
| [sacrysty](https://github.com/nisavid/sacrysty) | No | Yes | 2026-09-17 | 5 / 8 | 2 / 6 / 3 |
| [systools](https://github.com/nisavid/systools) | No | Yes | 2026-07-28 | 0 / 26 | 1 / 6 / 0 |
| [utilyze](https://github.com/nisavid/utilyze) | Yes | No | 2026-04-28 | 0 / 0 | 1 / 2 / 0 |
| [warp](https://github.com/nisavid/warp) | Yes | No | 2026-06-10 | 0 / 0 | 2 / 0 / 0 |
| [zsh-config](https://github.com/nisavid/zsh-config) | No | No | 2026-08-21 | 0 / 0 | 0 / 10 / 0 |
| **Public subtotal** | **6** | **16 of 22** | — | **394 / 481** | **43 / 528 / 66** |
| **Private aggregate, two repositories** | — | — | — | **31 / 55** | **1 / 32 / 0** |
| **Selected total** | **6** | — | — | **425 / 536** | **44 / 560 / 66** |

The 1,631 objects are a sizing observation, not 1,631 repairs or a count of
association pairs. I did not classify the full corpus, fetch private bodies,
or infer relationships from names. Six public repositories have Issues
disabled; that does not remove their PRs from scope or authorize enabling the
setting. Fork status also does not expand the set to upstream-owned objects.
Any upstream target needed to explain a selected object's relation must retain
its repository-qualified identity and an explicit read/write boundary.

## Decisions and downstream return contract

The later live graph adds [Qualify Development-link behavior under the chosen closure policy](https://github.com/nisavid/provingkit/issues/90),
blocked by the relation-policy decision. The repair-contract decision is in
turn blocked by that qualification and this inventory research. I verified
those native edges with complete connections. The qualification task must
return observed supported behavior before repair can promise state-preserving
historical native-link writes; it is outside the earlier count snapshot.

The selected repository set is settled. The remaining decisions are:

1. **Relation meaning and closure policy:** what proves contribution,
   which relations belong in each ledger and native surface, how uncertainty is
   represented, and when an Issue completion contract permits closure. Consume
   the platform findings before selecting automatic native-link behavior.
2. **Lifecycle and operation ownership:** the relation coordinator,
   Issue-body and native-link actuation owners, supported material-update
   triggers, and the handoffs through existing writer, publisher, and merge
   owners. Include preservation, concurrency, retry, unknown-outcome, and
   no-op behavior in the contract.
3. **Historical repair contract:** evidence thresholds for automatic
   versus ambiguous cases, treatment of historical and cross-repository
   limitations, public/private evidence handling, finite batches, recovery,
   and accounting for every selected object and supported association.
4. **Deployment increment:** select the exact candidate, supported Hatchery
   client surfaces, manager route, and coordinated change window without
   taking over the earlier preview rollout. A newer procedure revision alone cannot
   update a pinned artifact.

The producer's completion contract should name the canonical procedure and
each invocation pointer, supported input classes, current positive and negative
discovery evidence, behavior and failure evidence, and the reviewed immutable
revision. Deployment and retroactive consumers load that revision through
`capturing-agent-procedures`, verify the producer result before dependent work,
and return evidence identifying what they actually consumed. The coordinator
owns the acyclic dependency graph and the eventual tracker resolution.
