# Provingkit promotion and release-chain security assessment

The frozen public source is a coherent seven-member source-stage Kit, but it has no current path to one immutable Provingkit release. The chain fails closed at the public caller, committed-evaluation-receipt, producer/issuer, product-qualification, native-host, and final-release layers. This is a closed release gate, not evidence of an exploitable bypass, and completing this research does not make any member or route release-eligible.

## Evidence boundary and method

This result is bound to public Provingkit commit `e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08` and tree `3c256c2541ec60f4ded5d7baeaf929611700666e`. Every source citation below resolves in that immutable tree.

Public issue bodies, comments, assignments, pull-request refs, and repository refs are observations in the shipped [public issue snapshot](2026-09-05-provingkit-promotion-chain-public-context.json), captured at `2026-09-05T05:52:33.561Z`, SHA-256 `58be25dae19b6843db8754ef1da977c0a67ea3ce3f62b834b701d345eb70119c`. The shipped [eval, route, and graph snapshot](2026-09-05-provingkit-eval-and-route-context.json), generated at `2026-09-05T06:35:43.673Z`, has SHA-256 `ef56c55310cbc2b97c1ac76d3776c4193f71ade7be7639d35f92a07f4416ee75`. The [companion evidence](2026-09-04-provingkit-promotion-chain-evidence.json) records those hashes, the immutable source selection, preserved public refs, and the native-graph capture. These are shipped public evidence boundaries; I did not query or dynamically validate current GitHub state.

I performed read-only static tracing of source, configuration, registries, public callers, command entrypoints, tests, and workflows. I did not execute repository code or tests, run evals or inference, inspect a live host, use credentials, qualify a route, sign, install, publish, or perform hosted readback. The SHA-256 returned beside this report protects only the transport integrity of these Markdown bytes; it is not production attestation or release authority.

## Current source and evidence shape

The source definition requires all seven members, disallows a partial Provingkit selection, records no release-manifest instance, grants no release authority, and remains `source-stage-unreleased` [source definition, lines 4–137][s-definition]. Six members—Rolecasting, Tricritical, Versionkeeping, Mergecraft, Artifact Customs, and Tidesmith—are portable Agent Plugins. Task Witness is the seventh, code-only member with no portable skill or MCP surface [README, lines 3–45][s-readme]. The root marketplace file is a source projection of exactly those six portable plugins, not a publication [marketplace projection, lines 2–38][s-marketplace].

The retained source-lineage manifest still identifies six packages from an older `nisavid/agents` basis and omits Tidesmith [historical source manifest, lines 1–139][s-source-manifest]. The current source expressly classifies that manifest and the native qualification material as historical, pending a fresh rescout [README, lines 47–55][s-readme]. The final rescout is absent, and the refresh contract invalidates evidence when candidate identity, package bytes, contribution decisions, installed identity, discovery routes, or source revision/tree/content/license change [refresh contract, lines 88–144][s-refresh]. This supports a stale historical-evidence finding without asserting an exact time or age for the frozen source commit.

## Gate inventory

“Existing” means source or a contract exists but does not necessarily carry production authority. “Missing” means the decision, implementation, artifact, accepted review, or receipt is absent. “Stale” means evidence binds an older or different candidate. “Fixture-only” means test-owned authority cannot be promoted.

| Gate | Frozen evidence and exact gap | Independent authority and owner |
| --- | --- | --- |
| 1. Seven-member reconciliation and candidate freeze | **Existing:** the exact seven-member definition. **Stale:** the six-member lineage manifest. **Missing:** final installed-library rescout, refreshed source identities, terminal dispositions, affected-closure evidence, and one frozen candidate. | [Define the Provingkit release contract (#3)][i-3] owns final identities, rescout, contract, and evidence composition. [Review source-skill lineage with Daybreak (#5)][i-5] and [review and bind disposition evidence (#6)][i-6] retain their separate security scopes. |
| 2. Source-security acceptance | **Existing:** source-stage validators and a historical extraction review [extraction review, lines 330–376][s-extraction-review]. **Missing:** accepted exact-revision results for the manager-state/provenance/TOCTOU scope and the corrected behavior-level disposition/receipt scope. A clean source review is not host or product qualification. | The two security issues above own their reviews and remediation; neither can self-grant release eligibility. |
| 3. Committed per-skill evaluation receipts | **Existing but different:** `release/plugin-eval-policy.json` binds the `plugin-eval` tool/runtime and a calibration manifest; the baseline is a plugin-level token-cost sample [tool policy, lines 1–18][s-eval-policy] [calibration baseline, lines 1–23][s-eval-baseline]. The retained internal production path runs that executable for the six skill plugins and embeds its same-run projection in a release receipt [eval execution, lines 2895–2982][s-eval-run] [receipt composition, lines 3327–3389][s-eval-compose]. **Missing:** the later accepted Kit-wide contract—committed per-skill receipts bound to content-lock, eval, and fixture digests, with thresholds in `release/behavior-eval-policy.json`; CI must check those receipts and never execute evals [eval-gate decision][i-eval-decision]. Neither that policy nor committed per-skill receipts exists in this source tree. | [Define the eval receipt schema, policy, and source-stage check (#33)][i-33] owns schema/check/runner implementation. [Gate Mergecraft readiness and merge on eval receipts (#34)][i-34] owns PR-readiness and merge enforcement; [carry eval results in PR bodies (#28)][i-28] is a separate dependent. [Choose the producer and issuer boundary (#8)][i-8] owns issuance authority. The release-contract issue owns release composition and staleness/invalidation. Executable-produced output, a green check, or a digest is not the accepted committed receipt. |
| 4. Supported product routes and per-cell qualification | **Existing:** the public map defines a cell as one audited host plus one distinct supported harness/provider route and requires secret-free end-to-end coverage of every meaningful capability path [public release boundary decision][i-route-decision]. **Missing:** a current supported-route inventory, the mapping from the historical “six distributions” language to today’s six portable plugins plus code-only Task Witness, and every resulting qualification result. | [Research target-harness release and update routes (#1)][i-1] owns route facts; the release-contract issue owns the accepted current matrix and evidence contract. Host execution belongs to separately authorized qualification successors created or identified by the producer/issuer decision. |
| 5. Producer, issuer, and trust-boundary decision | **Missing:** selected Rolecasting execution producer, Tricritical review/adjudication producer, issuer identities, trust roots, candidate/build/route bindings, capabilities, and failure/recovery semantics. | The fresh HITL [producer and issuer decision (#8)][i-8] chooses these boundaries without implementing them. Its required fan-out keeps producer implementation, review/issuer implementation, independent security review, and host qualification separate [fan-out decision][i-8-fanout]. |
| 6. Current public-route implementation | **Missing by intentional source-stage barriers:** the Task Witness executable entrypoint always returns installation failure; Mergecraft required-review mode calls a helper that always raises “unavailable.” These fail before private-evidence parsing, the installed front door, provider trust, or a validator. | The producer/issuer decision must create or identify distinct native implementation successors for restoring or replacing the Task Witness client route and the Mergecraft required-review route before any host qualifier is asked to use them. The release-contract owner defines the required route; implementation and independent exact-artifact review remain separate. |
| 7. Rolecasting and Tricritical producer/issuer implementation | **Existing:** substantive validators. **Missing:** registered production producers and issuers, authenticated owning-product integrations, positive and fail-closed evidence, and accepted independent review. **Fixture-only:** tests inject synthetic trust. | Separate successors from the producer/issuer decision implement the Rolecasting and Tricritical boundaries; a separate Daybreak authority reviews the exact artifacts. A validator, candidate author, fixture, or coordinator cannot issue its own authority. |
| 8. Task Witness native-host receipts and canonical review | **Stale:** retained Linux evidence used an older candidate; retained macOS material was a host probe, not that candidate’s run [historical qualification, lines 1–7][s-history]. **Missing:** fresh macOS arm64 and Linux x86_64 create-new receipts for one immutable candidate, plus fresh product-attested Rolecasting and independent Tricritical evidence. | The future work-Mac and Hatchery tasks each own only their host observation. A receipt claims neither the other host nor product-route coverage, review independence, or release eligibility [host receipt, lines 1017–1061][s-host-receipt] [claim boundary, lines 1339–1340][s-host-boundary]. |
| 9. Promotion and discovery contract | **Existing but historical:** the retained TW4 design and disabled validator encode a sole-parent successor that flips `production_eligible` and adds a Task Witness marketplace route [retained promotion, lines 1453–1509][s-promotion]. **Current source conflict:** Task Witness is code-only and the marketplace projects only the six portable plugins. **Missing:** a current decision that retains, replaces, or removes that discovery assumption and defines any permitted final delta. | The release-contract issue owns this decision. This assessment does not select a marketplace, native-manager, or code-package route. Any retained assumption becomes current only through that decision and fresh dependent evidence. |
| 10. Detached Task Witness and whole-Kit manifests; final validation | **Existing:** historical design, internal parsers, and a whole-Kit schema requiring seven members and immutable source identity [Kit schema, lines 1–109][s-kit-schema]. **Missing:** authoritative manifest instances, reachable final entrypoints, a validation run against the accepted current promotion contract, and accepted output. The shipped Task Witness and generic public-release entrypoints reject final/production modes [Task Witness entrypoint, lines 4862–5014][s-tw-final-entry] [generic entrypoint, lines 3497–3675][s-public-entry]. | The release-contract issue defines composition. A coordinator may bind already authoritative facts; it observes or issues none. |
| 11. Source landing and identity preservation | **Missing:** the landing shape and evidence that the reviewed final successor is the released source identity. Current retained validation expects a sole-parent successor, so merge, squash, rebase, or an extra commit can change the identity [final validator, lines 3881–3941][s-final-validator]. | The release-contract issue decides landing/rebinding. Repository merge authority remains separate from review, issuance, signing, and release authority; a source merge authorizes none of them [contribution boundary, lines 15–18][s-contributing]. |
| 12. Version, tag, assets, signatures, hosted publication/readback, and release receipt | **Missing:** version/tag binding, asset set and digests, signing policy and signatures, GitHub Release and canonical-state publication, hosted readback, independent verifier receipt, and one agreeing release receipt. Recorded empty tag/release inventories are historical snapshot evidence, not a current query. | The release-contract issue defines the contract. [Publish the first signed Provingkit release (#36)][i-36] operates only after its blockers: GitHub Actions stays candidate-only; operator-present Hatchery authority signs and publishes; an independent work-Mac verifier reads back and accepts. |
| 13. Authenticated HTTPS executor | **Existing:** statically reachable Versionkeeping implementation and closed macOS/Linux/Windows provider selection. **Missing/disputed:** a durable exact-revision independent acceptance artifact. **Route-dependent:** the native graph does not make it an unconditional blocker. | [Support authenticated HTTPS publication (#4)][i-4] owns review-evidence reconciliation. The release-contract issue chooses an actuator; the release-ops issue revalidates and uses only the accepted route. |

## Two qualification planes

The historical handoff defines product qualification across audited host × supported provider-route cells, but the frozen source classifies that handoff as historical [route boundary, lines 56–99][s-route-boundary] [historical allowlist, lines 14–17][s-historical-allowlist]. The later public map retains the cell decision while its current body identifies a seven-member Kit with six portable plugins and code-only Task Witness [release map (#41)][i-map]. The supplied public record contains no superseding qualification decision, but it also contains no decision that mechanically reinterprets the old six-distribution count as the current six portable plugins.

The current matrix therefore has to be resolved without manufacturing a Cartesian product:

| Route named in public evidence | Work macOS | Linux Hatchery | What remains |
| --- | --- | --- | --- |
| Codex | A cell only if current route research establishes support. | A cell only if current route research establishes support. | The map’s “Codex” label must be reconciled with the Task Witness design’s separate ChatGPT Codex and Codex CLI/TUI surfaces [review profile, lines 1342–1381][s-review-profile]. |
| Claude / Claude Code | A cell only if supported. | A cell only if supported. | Current naming and provider-route identity must be fixed by route research. |
| Cursor | A distinct cell only if supported. | A distinct cell only if supported. | It cannot borrow Cursor Agent evidence. |
| Cursor Agent | A distinct cell only if supported. | A distinct cell only if supported. | It cannot borrow Cursor evidence. |
| Claude Desktop | The public decision identifies a macOS-only route. | Explicitly unsupported; no Linux cell. | The exact pinned installation source/procedure remains unresolved. |

For each accepted cell, the public decision requires a secret-free local end-to-end result for every meaningfully distinct capability path of each applicable portable distribution, recording route, capability, fixture/case, result, and failure class. No such current cell evidence was supplied, and this assessment performed none.

Task Witness’s two native receipts are a different plane: one receipt covers exactly macOS arm64 and one exactly Linux x86_64, binding candidate, platform profile, runtime closure, and suite results. They do not prove any portable plugin/provider cell. Conversely, product-route smoke evidence does not satisfy either native receipt. The Task Witness canonical review’s product-attested ChatGPT Codex requirement is a third, narrow evidence claim; it does not qualify Claude, Cursor, Cursor Agent, or every Codex surface.

## Static caller-to-sink validation

### RC-01 — Rolecasting new-publication reachability

**Claim.** No Rolecasting evidence can reach Task Witness’s accepted non-historical publication sink through the current public routes and registered trust chain.

**Current callers and entrypoints.** Mergecraft’s public create and update implementations call `validate_required_review` for required publication [create required-review call, lines 446–450][s-mergecraft-create-call] [update required-review call, lines 224–234][s-mergecraft-update-call]. Required mode then calls `_invoke_task_witness`, but that helper unconditionally raises that native validation is unavailable [required-review call, lines 1524–1550][s-mergecraft-required] [direct stub, lines 1105–1137][s-mergecraft-stub]. Separately, executing the current Task Witness client reaches `entrypoint_main`, which unconditionally returns `EXIT_INSTALLATION`; the retained internal `main` is not selected by `__main__` [Task Witness client, lines 8976–9048][s-tw-client]. Containment tests assert both failures occur before client setup, the authenticated front door, or supervisor [containment tests, lines 186–245][s-containment]. Package documentation identifies both as intentional source-stage barriers [Task Witness boundary, lines 10–23][s-tw-readme] [Mergecraft boundary, lines 12–22][s-mergecraft-readme].

**Downstream boundary after route restoration.** Rolecasting’s provider declaration registers a validator but has empty producer and issuer arrays [Rolecasting provider, line 1][s-role-provider]. Task Witness’s retained trust parser requires nonempty producers and issuers, binds each producer to a registered validator, and admits active usable lifecycles; the launcher accepts only a producer/validator pair authorized by selected trust [trust parser, lines 2177–2289][s-tw-trust] [accepted sink, lines 7926–8023][s-tw-accept]. The Rolecasting validator checks supplied producer and issuer-backed model/result facts, but it does not create or authenticate an owning-product execution [Rolecasting validator, lines 350–539][s-role-validator].

The immediate blocker is therefore the two direct source-stage stubs. The [older producer/issuer checkpoint][i-2-producer] remains correct only in the narrow sense that the missing producer chain is a later transitive Mergecraft blocker after the Mergecraft and Task Witness public routes are restored or replaced. Fixtures and validator logic prove only their narrow source contracts. No authorized runtime, installed trust snapshot, credentials, or product attestation was supplied. Confidence is high for this frozen-source reachability claim and intentionally does not extend to an external implementation.

### TC-01 — Tricritical terminal-review reachability

**Claim.** No fresh Tricritical terminal review can reach Task Witness’s accepted new-publication sink through the current public routes and registered trust chain.

The same direct Task Witness and Mergecraft barriers apply first. Downstream of a future reachable route, Tricritical’s provider declaration registers one validator and no producer or issuer [Tricritical provider, line 1][s-tri-provider]. Its validator requires a trusted producer, a valid cycle and successor chain, independently complete execution, no unresolved actionable finding, passed unchanged verification, and a bare-clean terminal; its projection embeds Rolecasting as `final_dispatch` [Tricritical validator, lines 1585–1742][s-tri-validator]. Tests that inject producer/issuer identities establish parser and derivation behavior only [fixture trust, lines 230–251][s-tri-fixture].

Rolecasting execution evidence must therefore precede Tricritical review evidence, but neither can be generated authoritatively by the candidate, a fixture, a validator, or the release coordinator. The producer/issuer decision must arrange separate implementation successors for the two public-route stubs and the downstream Rolecasting and Tricritical producer/issuer gaps, followed by independent exact-artifact review. No implementation is selected here.

### REL-01 — final release-evidence integration

**Claim.** The frozen source cannot currently produce an accepted Task Witness final-evidence set or whole-Kit release instance.

Task Witness is registered `production_eligible: false` [registration, lines 1–23][s-registration]. Its current client, qualification runner, qualification suite, Task Witness final validator, generic public-release validator, and prepared wrapper all reject later-release execution at their public entrypoints [Task Witness README, lines 3–23][s-tw-readme] [qualification runner, lines 5953–5960][s-qualification-runner] [qualification suite, lines 4140–4151][s-qualification-suite] [Task Witness final entrypoint, lines 5001–5014][s-tw-final-entry] [generic entrypoint, lines 3663–3675][s-public-entry] [prepared wrapper, lines 17–26][s-prepared-wrapper]. The internal final validator can parse two exact host receipts, enforce a common candidate and bridge history, check a sole-parent promotion successor, and launch canonical review, but that retained implementation is not a reachable production route [final validator, lines 3822–3955][s-final-validator]. The whole-Kit definition lists no manifest instance and grants no release authority.

No native receipt, product-route result, canonical production review, committed per-skill eval receipt set, current promotion decision, whole-Kit manifest, production validation output, signature, hosted publication, or readback was supplied. Internal contracts, schemas, fixture successes, hashes, same-job projections, and green source tests cannot fill those independent authority gaps.

## Partial order and authority separation

The minimum evidence order is:

1. Implement the committed-receipt contract under the eval-schema issue before its native dependents: the supplemental graph records the schema/check issue with no blocker and with the PR-body and Mergecraft-gate issues as dependents; the Mergecraft gate is blocked by the schema/check issue. Before a receipt is treated as authoritative, the producer/issuer decision must settle issuance and the release-contract issue must settle composition and staleness. Those semantic prerequisites are not represented as native blockers on the two eval tickets.
2. Settle every candidate-changing prerequisite: exact-revision source-security findings, supported route identities, producer/issuer and trust boundaries, and the current release/promotion contract. The producer/issuer decision must create or identify separate Task Witness-client and Mergecraft-required-review implementation successors in addition to its producer, issuer/review, security-review, and host-qualification successors.
3. Implement the selected boundaries without combining authority: public route code, Rolecasting producer integration, Tricritical review/adjudication producer and issuer, and any accepted receipt issuance path each receive exact-artifact independent review. Host qualification cannot start while its public route still fails before parsing or authentication.
4. Complete the source refresh workflow: final rescout, refreshed identities, source reconciliation, terminal dispositions, candidate freeze, affected-closure evaluation, and capture of bound refresh evidence [refresh workflow, lines 799–810][s-refresh-order]. Any implementation or accepted retained-input change before freeze reopens the affected work.
5. From one immutable candidate, generate three non-substitutable evidence branches: all accepted product host-route cells; the macOS and Linux Task Witness native receipts; and Rolecasting followed by Tricritical canonical evidence. The two native receipts have no data dependency on each other, although the historical TW4 design lists macOS then Linux; the release-contract owner must decide whether that historical serialization remains normative [retained creation order, lines 1511–1532][s-creation-order].
6. The release-contract owner reconciles the code-only Task Witness shape with the retained promotion/discovery assumption and defines the permitted final successor. Only then may a coordinator create detached evidence from already authoritative inputs and final validation consume it without mutation. The retained two-path successor is not presumed.
7. Preserve the validated identity through source integration, then bind version, tag, assets, digests, signatures, and canonical hosted state to that same identity. Publication precedes independent hosted readback; readback precedes final acceptance and the agreeing release receipt.
8. If the accepted publication route uses Versionkeeping over HTTPS, the exact executor revision, host provider boundary, and independent review evidence must be accepted before the release operator actuates it.

The authorities remain non-substitutable:

- Each product host-route cell and each native host owns only what it observed.
- Rolecasting authenticates product execution; Tricritical independently reviews and adjudicates.
- A validator checks evidence; it does not produce, issue, sign, or publish it.
- The eval runner may calculate output; only the accepted issuer boundary can make a committed receipt authoritative.
- The manifest coordinator binds facts and creates none.
- Source reviewers and repository merge authority neither sign nor release.
- GitHub Actions may build, test, and attest candidates, but the public release issue grants it no production signing authority.
- Operator-present Hatchery signing/publication and independent work-Mac readback are separate authority domains.

## Snapshot graph and owners

The shipped graph evidence records 258 issues, 1,025 directional relations, and terminal pagination, with no topology, state, or assignment delta in the supplemental capture. These are snapshot facts, not live claims.

- [Audit the promotion and release chain (#2)][i-2] was open and assigned to `nisavid`; its two source-cutover blockers were closed, and it directly blocked the producer/issuer decision, the release contract, and first-release publication.
- The producer/issuer decision was open, unassigned, and blocked only by the audit. Its fresh-entry rule requires a new HITL context after the audit is resolved and eligibility is checked; this research does not dispatch it [research-only correction][i-2-correction].
- [Define the Provingkit release contract (#3)][i-3] was open and unassigned, directly blocked by [target-harness route research (#1)][i-1], this audit, both source-security issues, the producer/issuer decision, [portable GitHub Markdown implementation (#9)][i-9], [Mergecraft feedback routing (#10)][i-10], and [the Tidesmith map (#12)][i-12]. Closing the audit removes only its edge.
- [Publish the first signed release (#36)][i-36] was open and unassigned, directly blocked by this audit, the release contract, the producer/issuer decision, [the README rework (#32)][i-32], and [release-ops acceptance (#266)][i-266].
- Authenticated HTTPS review was open and unassigned with no native blocker or dependent edge. Graph absence does not decide whether the selected release route needs it.
- Route research was open and assigned to `nisavid`. The eval schema/check and Mergecraft gate tickets were open and unassigned; the former had no native blocker and blocked the latter and the PR-body ticket, while the latter was blocked only by the former.

Retained [Provingkit PR #40][i-pr40], [agents PR #69][i-pr69], and `refs/heads/retained/agents-pr-69` are preserved evidence inputs at the revisions recorded in the public snapshot. Selecting any of their bytes would create a changed candidate and trigger affected revalidation; preservation, draft status, or a source merge grants no producer, issuer, qualification, signing, or release authority [preserved-input record][i-2-inputs].

## Evidence invalidation

| Change | Evidence that becomes stale |
| --- | --- |
| Candidate commit/tree, package byte, identity artifact, source decision, source identity/license, installed membership, or discovery route | Final rescout and source manifest for the affected closure; any per-skill receipt bound to changed content; product-route cells; both native receipts because they bind the exact candidate; Rolecasting/Tricritical evidence; detached/whole-Kit manifests; final validation; and downstream artifacts that name the prior identity. |
| Eval definition, fixture, content lock, threshold policy, executor/grader identity, candidate revision, waiver, or receipt bytes | The affected committed per-skill receipt and its PR-body/readiness/merge proof. Release composition and every downstream artifact that consumed the prior receipt become stale according to the rule still to be defined by the release-contract owner. A fresh same-job run cannot patch the old receipt. |
| Task Witness client route, Mergecraft required-review route, provider declaration, producer/issuer implementation, trust root, capability, lifecycle, or authenticated integration | The affected implementation review, Rolecasting/Tricritical evidence, and route qualification. If candidate bytes change, native receipts and all candidate-bound evidence also become stale. |
| Supported route set, provider identity, installation source, host runtime, account boundary, or one host-route observation | Only the affected product cell may be regenerated when shared candidate and contract inputs remain exact. It neither creates nor invalidates a Task Witness native receipt unless a shared bound input changed. |
| Native platform profile, runtime closure, toolchain, sandbox, or host observation | That host’s Task Witness receipt and downstream manifest/final validation. The other host receipt may survive only if all common candidate and bridge inputs remain exact. |
| Review input, dispatch, assurance minimum, issuer, critic scope, finding, adjudication, loop state, or candidate revision | The affected Rolecasting/Tricritical evidence and downstream validation. A semantic repair creates a new candidate and invalidates both native receipts as well. |
| Promotion/discovery decision, permitted delta, or final commit/tree | Detached and whole-Kit manifests, final validation, integration binding, tag/assets/signatures, publication/readback, and release receipts. Candidate qualification can survive only if its bytes and every trust input remain exact and the current contract expressly permits rebinding. |
| Merge, squash, rebase, or extra commit after final validation | The final Git identity and every downstream binding. The retained validator’s sole-parent rule cannot be repaired by copying a digest forward. |
| Asset rebuild, signing policy/key identity, tag target, hosted object, or canonical-state change | The affected signature, publication/readback proof, verifier acceptance, and release receipt. Source qualification survives only when the validated source identity is unchanged. |
| Versionkeeping executor or credential-provider boundary, when selected | The executor’s independent review and route execution evidence. It does not invalidate unrelated product evidence if the release contract selects another actuator. |

## Authenticated HTTPS executor

The frozen source has a reachable Versionkeeping command that reads exact reviewed plan bytes and a separately supplied digest before calling the executor [executor CLI, lines 1–55][s-vk-cli]. For HTTPS, the executor validates the ready plan, repository, object identities, destination, endpoint fingerprint, default branch, configuration digest, and exact lease; enables credentials before remote probes; makes one push without blind retry; and verifies the resulting ref [executor, lines 265–387][s-vk-execution].

The credential-provider set is closed: codesign-verified system `git-credential-osxkeychain` on macOS, a trusted system `git-credential-cache` with a credential already in its private memory cache on Linux, and allowlisted Git Credential Manager from the selected machine-wide Git for Windows installation. Missing, redirected, mutable, or unsupported providers fail with `HTTPS_CREDENTIAL_PROVIDER_UNAVAILABLE` before push. Ambient credential and HTTP configuration is rejected or cleared, prompting is disabled, and credential bytes remain inside Git’s helper protocol rather than plans, arguments, diagnostics, receipts, or repository configuration [HTTPS contract, lines 80–134 and 165–190][s-vk-contract] [provider checks, lines 205–265][s-vk-provider] [provider selection, lines 1103–1137][s-vk-selection].

That establishes current source reachability, not production acceptance. The workflow has read-only repository permission and exercises provider tests; it does not push a release or confer independent authority [workflow, lines 12–54][s-vk-workflow]. The public record says implementation merged and cross-platform checks exist, while a later checkpoint says the PR’s clean-review assertion and durable issue evidence do not identify the same exact review artifact [implementation checkpoint][i-4-merged] [review discrepancy][i-4-discrepancy].

The HTTPS path is a hard gate only if the release contract selects it for a required source or canonical-state mutation and release operations must use it. An independently accepted SSH/local Versionkeeping route or other release actuator would not inherit this HTTPS review gap. The release-contract issue chooses; the publication issue revalidates and operates; the HTTPS issue reconciles its review. Native graph topology cannot make that design choice.

## Remaining decisions and proof gaps

- [Define the eval receipt schema, behavior policy, and source-stage check (#33)][i-33] must implement the accepted receipt shape and checker. [Gate Mergecraft readiness and merge (#34)][i-34] must consume that contract. Issuance remains with the producer/issuer decision; release composition and invalidation remain with the release contract. The missing native dependency representation among those authorities is a graph/acceptance proof gap, not permission to collapse them.
- [Research target-harness routes (#1)][i-1] must identify current host support and exact route identities. The release-contract owner must reconcile the historical six-distribution decision with six portable plugins plus code-only Task Witness and name every required current cell. The future host owners must produce the cells; Task Witness receipts cannot stand in for them.
- [Choose the producer and issuer boundary (#8)][i-8] must choose identities and trust semantics and create or identify distinct successors for Task Witness client-route restoration or replacement, Mergecraft required-review restoration or replacement, Rolecasting producer implementation, Tricritical review/adjudication producer and issuer implementation, independent Daybreak design/exact-artifact review, and separate work-Mac and Hatchery qualification. It must not combine implementation, review, issuance, or qualification authority.
- The two source-security owners must complete exact-revision review and any separately reviewed remediation. Their result feeds but does not replace product or host evidence.
- [Define the Provingkit release contract (#3)][i-3] must settle the fresh rescout and seven-member identities; current eval-receipt composition and staleness; route matrix; code-only Task Witness promotion/discovery semantics; detached and whole-Kit manifests; final landing/rebinding; versions, tags, assets, digests, signing, marketplace/native distribution, canonical state, readback, receipts, update, revocation, reinstall, and rollback; and whether the HTTPS actuator is required.
- [Support authenticated HTTPS publication (#4)][i-4] must link the exact reviewed executor revision to durable independent acceptance if that path remains eligible.
- [Publish the first signed release (#36)][i-36] may act only after all native and semantic gates close, then must keep preparation, operator-present signing/publication, and independent readback separate.
- The retained drafts remain evidence only. If selected by a future owner, their exact bytes enter reconciliation before candidate freeze and every dependent pass must run on the resulting revision.

No operator decision is needed to complete this research finding. The unresolved choices belong to the named future tickets. The release becomes reachable only after one current contract binds one immutable seven-member candidate to authoritative committed eval receipts, every accepted product route, two distinct native Task Witness receipts, authenticated Rolecasting execution, independent Tricritical terminal review, an accepted current promotion/discovery shape, immutable manifests and final validation, identity-preserving integration, and separately authorized signing, publication, hosted readback, and final receipt. None of those missing authorities is created by this assessment.

[s-definition]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/release/provingkit/definition-v1.json#L4-L137
[s-readme]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/README.md#L3-L55
[s-marketplace]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/.claude-plugin/marketplace.json#L2-L38
[s-source-manifest]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/release/source-skill-lineage/source-manifest.json#L1-L139
[s-refresh]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/release/source-skill-disposition/release-refresh-contract.json#L88-L144
[s-extraction-review]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/release/provingkit/review-evidence/issue-81/538723c92a3103c15a3c835f2161332239a8cb13-daybreak-security-authority-v3.json#L330-L376
[s-eval-policy]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/release/plugin-eval-policy.json#L1-L18
[s-eval-baseline]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/release/plugin-eval-baseline-v1.json#L1-L23
[s-eval-run]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/scripts/validate_public_release.py#L2895-L2982
[s-eval-compose]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/scripts/validate_public_release.py#L3327-L3389
[s-history]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/qualification/historical/README.md#L1-L7
[s-host-receipt]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/docs/superpowers/specs/2026-08-12-task-witness-tw4-migration-and-qualification-design.md#L1017-L1061
[s-host-boundary]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/docs/superpowers/specs/2026-08-12-task-witness-tw4-migration-and-qualification-design.md#L1339-L1340
[s-promotion]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/docs/superpowers/specs/2026-08-12-task-witness-tw4-migration-and-qualification-design.md#L1453-L1509
[s-kit-schema]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/release/provingkit/release-manifest-v1.schema.json#L1-L109
[s-tw-final-entry]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/scripts/validate_task_witness.py#L4862-L5014
[s-public-entry]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/scripts/validate_public_release.py#L3497-L3675
[s-final-validator]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/scripts/validate_task_witness.py#L3822-L3955
[s-contributing]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/CONTRIBUTING.md#L15-L18
[s-route-boundary]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/docs/superpowers/research/2026-08-24-cross-repository-implementation-handoff.md#L56-L99
[s-historical-allowlist]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/release/provingkit/historical-identity-allowlist-v1.json#L14-L17
[s-review-profile]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/docs/superpowers/specs/2026-08-12-task-witness-tw4-migration-and-qualification-design.md#L1342-L1381
[s-mergecraft-create-call]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/plugins/mergecraft/skills/publishing-reviewable-prs/scripts/create_reviewable_pr.py#L446-L450
[s-mergecraft-update-call]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/plugins/mergecraft/skills/publishing-reviewable-prs/scripts/update_reviewable_pr.py#L224-L234
[s-mergecraft-required]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/plugins/mergecraft/skills/publishing-reviewable-prs/scripts/required_review.py#L1524-L1550
[s-mergecraft-stub]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/plugins/mergecraft/skills/publishing-reviewable-prs/scripts/required_review.py#L1105-L1137
[s-tw-client]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/plugins/task-witness/client/task_witness_client.py#L8976-L9048
[s-containment]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/tests/test_later_release_security_containment.py#L186-L245
[s-tw-readme]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/plugins/task-witness/README.md#L3-L23
[s-mergecraft-readme]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/plugins/mergecraft/README.md#L12-L22
[s-role-provider]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/plugins/rolecasting/task-witness-provider.json#L1-L1
[s-tri-provider]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/plugins/tricritical/task-witness-provider.json#L1-L1
[s-tw-trust]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/plugins/task-witness/client/task_witness_client.py#L2177-L2289
[s-tw-accept]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/plugins/task-witness/client/task_witness_client.py#L7926-L8023
[s-role-validator]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/plugins/rolecasting/skills/delegating-cross-agent-work/scripts/dispatch_evidence.py#L350-L539
[s-tri-validator]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/plugins/tricritical/skills/loop/scripts/review_evidence.py#L1585-L1742
[s-tri-fixture]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/tests/plugins/test_tricritical_review_evidence.py#L230-L251
[s-registration]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/release/task-witness/public-release-registration.json#L1-L23
[s-qualification-runner]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/scripts/run_task_witness_qualification.py#L5953-L5960
[s-qualification-suite]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/scripts/run_task_witness_qualification_suite.py#L4140-L4151
[s-prepared-wrapper]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/scripts/run_prepared_release_validation.sh#L17-L26
[s-refresh-order]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/release/source-skill-disposition/release-refresh-contract.json#L799-L810
[s-creation-order]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/docs/superpowers/specs/2026-08-12-task-witness-tw4-migration-and-qualification-design.md#L1511-L1532
[s-vk-cli]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/plugins/versionkeeping/skills/checkpointing-and-publishing-git-work/scripts/execute_git_publication.py#L1-L55
[s-vk-execution]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/plugins/versionkeeping/skills/checkpointing-and-publishing-git-work/scripts/git_publication/execution.py#L265-L387
[s-vk-contract]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/plugins/versionkeeping/skills/checkpointing-and-publishing-git-work/references/publication-execution.md#L80-L190
[s-vk-provider]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/plugins/versionkeeping/skills/checkpointing-and-publishing-git-work/scripts/git_publication/adapter.py#L205-L265
[s-vk-selection]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/plugins/versionkeeping/skills/checkpointing-and-publishing-git-work/scripts/git_publication/adapter.py#L1103-L1137
[s-vk-workflow]: https://github.com/nisavid/provingkit/blob/e7965b0a2ad5c4f96dad8c2eea97f2d3d6db5c08/.github/workflows/versionkeeping-native-credentials.yml#L12-L54

[i-map]: https://github.com/nisavid/agents/issues/41
[i-route-decision]: https://github.com/nisavid/agents/issues/41#issuecomment-5407043582
[i-eval-decision]: https://github.com/nisavid/agents/issues/41#issuecomment-5524459718
[i-1]: https://github.com/nisavid/provingkit/issues/1
[i-2]: https://github.com/nisavid/provingkit/issues/2
[i-2-producer]: https://github.com/nisavid/provingkit/issues/2#issuecomment-5498560695
[i-2-correction]: https://github.com/nisavid/provingkit/issues/2#issuecomment-5498560761
[i-2-inputs]: https://github.com/nisavid/provingkit/issues/2#issuecomment-5548103388
[i-3]: https://github.com/nisavid/provingkit/issues/3
[i-4]: https://github.com/nisavid/provingkit/issues/4
[i-4-merged]: https://github.com/nisavid/provingkit/issues/4#issuecomment-5498561428
[i-4-discrepancy]: https://github.com/nisavid/provingkit/issues/4#issuecomment-5498561527
[i-5]: https://github.com/nisavid/provingkit/issues/5
[i-6]: https://github.com/nisavid/provingkit/issues/6
[i-8]: https://github.com/nisavid/provingkit/issues/8
[i-8-fanout]: https://github.com/nisavid/provingkit/issues/8#issuecomment-5498563281
[i-9]: https://github.com/nisavid/provingkit/issues/9
[i-10]: https://github.com/nisavid/provingkit/issues/10
[i-12]: https://github.com/nisavid/provingkit/issues/12
[i-28]: https://github.com/nisavid/provingkit/issues/28
[i-32]: https://github.com/nisavid/provingkit/issues/32
[i-33]: https://github.com/nisavid/provingkit/issues/33
[i-34]: https://github.com/nisavid/provingkit/issues/34
[i-36]: https://github.com/nisavid/provingkit/issues/36
[i-266]: https://github.com/nisavid/dotfiles/issues/266
[i-pr40]: https://github.com/nisavid/provingkit/pull/40
[i-pr69]: https://github.com/nisavid/agents/pull/69
