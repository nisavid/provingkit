DONE_WITH_CONCERNS

One prospective observation can establish when a bounded claim has usable evidence, what preparing that evidence costs, and whether a useful early delivery point exists. The selected workload is concrete, but its eligible window and future artifacts still require admission checks. This proposal delivers no model hint and measures no intervention effect.

## Bound workload and question

Observe the capability assessment for [issue 548](https://github.com/nisavid/provingkit/issues/548), on branch `ivan/research/peer-portfolio-sys1-548`, starting from the metadata-bound base `61b99e73ebedf8afb33b28a531daea8089504394`.

The selected report is `docs/superpowers/research/2026-10-12-system-one-portfolio-capabilities.md`. Select its **capability/source/evidence table and accompanying claims about what each mechanism can and cannot prove** before inspecting its content.

Frozen workload metadata records that the report did not exist at its check, ordinary work was authorized, observation was unaccepted, and the owner would continue without waiting. That is historical readiness evidence, not proof that the window remains open.

The observation answers:

1. When do one material assertion and its ordinary citations become available?
2. When can the existing claim producer consume them?
3. What selection, retrieval, and preparation work separates those events?
4. What ordinary checking, reuse, correction, review, and publication reconciliation subsequently occur?

Distinguish two opportunities: replacing identifiable support-checking work, and adding earlier independent error checking. Prior author judgment does not exclude the second. A baseline defect is unnecessary for exploring either hypothesis. The controlling qualification is in [the joined investigation README](docs/superpowers/research/evidence/jev-axi-integration-investigations-2026-10-12/README.md).

## Eligibility and admission

Perform the following checks twice: immediately before accepting the contract, and immediately before its first content acquisition. Preserve both timestamps and results. These are proposed checks; I did not perform them against the foreign worktree.

| Check | Required result | Failure disposition |
| --- | --- | --- |
| Workload identity | The private binding resolves to the metadata-named worktree, repository, branch, and authorized report; the bound base remains the workload’s ancestor. Record current HEAD separately. | Stop on mismatch; do not search for another workload. |
| Ordinary task state | Current, explicit owner-supplied task metadata identifies this increment, its next ordinary draft checkpoint, and whether that checkpoint or final review has already begun. | Unknown state means `eligibility_unestablished`; retain the missing fact. |
| Prospective window | The selected first ordinary draft checkpoint has not already passed, and final review of this increment has not begun. | Record `missed_opportunity`. No retrospective collection or automatic substitution. |
| Artifact access | Exact report path and specifically named task-owned evidence artifacts are accessible through the accepted read-only route. | Stop or narrow the accepted observation before collection. |
| Collection authority | Acceptance names collector, permitted local copies, artifact destinations, bounds, and permitted metadata/event access. | Preparation alone supplies no collection authority. |
| Current-source correspondence | Branch, HEAD, report path, and task identifier agree; any report already present has an owner-confirmed checkpoint identity. | An unexplained file at the right path is insufficient. |

The owner need not pause or create a checkpoint. If work advances between acceptance and acquisition, the execution-admission check records the missed window. An absent file alone cannot prove that review has not started elsewhere.

HEAD movement caused by ordinary task work is expected. A branch switch, rewritten ancestry, different report, or changed increment is workload drift and terminates this invocation. A different current HEAD is not permission to retain stale artifact identities.

## Assertion selection

At the first eligible ordinary draft checkpoint, select the first material, externally checkable assertion in the frozen section’s document order. Include table cells. A material assertion says something consequential about a mechanism’s capability, limitation, or evidentiary warrant; exclude headings, questions, plans, and bare links.

Select without checking whether the assertion is wrong. Preserve:

- The exact assertion text, enclosing paragraph or table row, and line coordinates.
- Its ordinary citation links and stated source roles.
- One or two cited sources on which that complete assertion rests.
- Selection time, checkpoint identity, and selection actions.

If the first material assertion lacks citations, requires more than two sources, or cannot be separated from a compound assertion without changing its meaning, retain it as the selected case and record that limitation. Do not skip to a easier or known-defective claim. Do not add sources merely to rescue readiness.

Freeze the assertion identity after selection. Later edits form its revision lineage; they do not restart selection. If the assertion disappears, preserve deletion as an outcome.

## Sources, forms, and identities

Use task-owned artifacts and ordinary tool-result records expressly named at admission. No transcript importer, private-history reconstruction, directory crawl, new hook, or broad collector is required.

| Binding | Accepted observation form | Identity and acquisition rule |
| --- | --- | --- |
| Draft | Complete UTF-8 Markdown file at an ordinary checkpoint; alternatively, its existing Git blob | Repository-relative path, byte count, SHA-256, checkpoint time, current HEAD, and whether bytes equal that committed path. Preserve exact bytes. |
| Claim sources | One or two complete cited public source artifacts already retained by ordinary work, or existing local Git blobs | Preserve ordinary citation, source role, complete bytes, digest, and original acquisition/revision information where available. Do not fetch missing sources for the observation. |
| Review | Existing task-owned review result and its candidate binding | Preserve reviewer findings and reviewed commit or file digests. A review without that association cannot establish which draft it covered. |
| Verification | Existing task-owned verification record relevant to this report | Preserve recorded checks, outputs, and checked revision. A worker’s statement that a check passed remains a report unless its result is retained. |
| Publication preparation | Existing candidate identity/comparison, bounded diff, ordinary explanation, and selected review/verification references | Preserve comparison kind, endpoints, changed paths, and evidence associations. Keep intended publication distinct from observed publication. |

A local file snapshot is a valid observation artifact but **not a supported claim-producer input**. The current [`claim_producer.py`](docs/superpowers/research/evidence/jev-axi-comparison-producers-2026-10-07/claim_producer.py), `read_blob` and `validate`, requires full commit identities, regular blob paths, expected digests, and one or two sources. It also requires the assertion on its designated draft line within valid context coordinates. It does not resolve citations or assess semantic support.

Accordingly, record three separate states:

- `observationally_available`: exact draft and cited evidence bytes can be retained.
- `producer_ready`: the existing reader can acquire all required committed blobs with matching identities and valid coordinates.
- `semantically_adequate_for_question`: a later evidence assessment can interpret the assertion’s referents and supplied sources. Producer readiness alone does not establish this.

Do not create an extra commit. If ordinary work later provides a commit, record the later readiness time; do not backdate it to the file snapshot. URL-only sources, uncommitted local captures, or citations unavailable locally may remain useful ordinary evidence while making this producer unavailable.

Recheck the live binding before each acquisition. For a changing file, obtain pre-read and post-read identity metadata and hash the copied bytes. If the checkpoint changes during acquisition, preserve the attempt as unstable and stop that checkpoint’s capture; do not silently retry. A snapshot’s stable bytes establish that copy, not the author’s entire prior knowledge.

## Events and checkpoints

Use one small coordinator-owned observation record. Each entry contains event type, observed time, occurrence time if independently recorded, artifact identity, evidence class, and accounting reference. Unknown occurrence time remains unknown.

| Event/checkpoint | Retain | Interpretation |
| --- | --- | --- |
| Acceptance and admission | Both eligibility results, frozen section and selection rule, authority, current workload identity | Establish the prospective boundary. |
| C1: first ordinary draft checkpoint before final review | Selected assertion, context, citations, source identities, explicit source-availability evidence | Establish the first observed preparation point. |
| Source readiness | Existing ordinary acquisition result or artifact creation record; observation acquisition time separately | Artifact existence proves availability by that time. It does not prove when the author first received or understood it. |
| Ordinary support explanation, reads, edits, and reuse | Specifically available task-owned records, bounded diffs, and cited synthesis/review-package uses | Retained actions establish visible work. Delivered material does not prove attention or internal reasoning. |
| Review submission and result | Submission/candidate identity and ordinary review record | Distinguish before-review readiness from readiness after checking. |
| C2: review result and resulting ordinary revision | Findings, selected-claim edit lineage, updated source/candidate associations | Show correction, retained claim, deletion, disagreement, or unresolved support. |
| C3: ordinary publication preparation | Final candidate, selected records, comparison, changed-text inspection evidence, reconciliation explanation | Identify actual remaining navigation and interpretation work. |
| Terminal event | Reason, final observed state, missing events, partial outputs, all incurred costs | Close this invocation without repairing gaps. |

Capture C2 when the ordinary review result and its resulting revision are available. If additional review rounds occur, retain their identities and findings only when already present in the named ordinary records. The three-checkpoint bound does not authorize collecting every intermediate draft.

At C3, the current [`coverage_producer.py`](docs/superpowers/research/evidence/jev-axi-comparison-producers-2026-10-07/coverage_producer.py) supports an explicit direct-parent commit comparison, caller-selected committed verification/review sources, and explicitly supplied overlays for a derived snapshot. It does not discover applicable reviews or establish an outgoing push range. An overlay snapshot is not a historical commit or observed publication.

This observation need not run that producer. Record whether ordinary inputs satisfy its boundary. Its whole-tree inventory reads and additional outputs would need explicit collection-budget admission before any invocation; they are not implied by observing the ordinary candidate.

## Acquisition limits

Propose these ceilings for the joined contract:

| Resource | Ceiling |
| --- | --- |
| Workloads/assertions/sources | One workload, one selected assertion, one or two claim sources |
| Content checkpoints | Three: C1, C2, C3 |
| Observation input artifacts | Nine complete copies maximum: three drafts, two sources, one review record, one verification record, one publication explanation, one bounded candidate diff |
| Per input artifact | 1 MiB |
| Gross observation content reads | 16 MiB total, including repeated hashing/reads, selected Git output, and any admitted producer input reads |
| Retained evidence | 12 MiB total; no silent truncation |
| Bookkeeping | One event/accounting record and one identity manifest, together at most 256 KiB |
| Execution duration | 60 minutes wall time after successful execution admission; pauses count |
| Acquisition retries | Zero automatic retries |
| Producer invocations | Zero by default; at most one claim-preparation invocation only if separately included in the accepted contract and all inputs are naturally producer-ready |

The claim-preparation option adds at most one case specification and six producer artifacts: up to three `.source` copies, `packet.json`, `packet.md`, and `receipt.json`. They share the same byte ceilings; duplicate evidence still consumes read/storage budget. Producer output remains with the observer, withholding any hint from the working author.

The producer has no built-in resource ceiling. An admitted invocation therefore needs prechecked blob sizes, at most 60 seconds runtime, and retained partial output on timeout. Never reuse or overwrite its output directory. Its receipt measures blob bytes and producer duration, not all selection work, physical I/O, or whole-task cost. `quotation_status` appears in JSON, not the rendered Markdown.

Use existing ordinary checkpoint visibility. Do not install a watch process or repeatedly poll for missing artifacts. A terminal read may collect available named artifacts once within the remaining budget. If a just-finished result has not become available, retain `result_not_persisted` rather than waiting for it.

Exceeding any bound ends acquisition with a partial observation. It does not stop the ordinary task or enlarge this contract.

## Interference and stale evidence

Record collector overlap with ordinary work, observation-specific requests, author/reviewer awareness where known, and any necessary correction delivered through the ordinary workflow. Do not infer no interference from silence.

The collector should neither ask the author to settle the selected assertion for measurement nor supply an observer-created support judgment. An unavoidable ordinary correction remains allowed, but makes subsequent work an affected baseline. Account for that limitation rather than withholding needed correction.

Every claim edit or source change invalidates the corresponding earlier readiness/adequacy association. A new candidate needs a current review association. Preserve earlier bytes and findings; a final commit cannot prove what an earlier review checked. This follows the stale-source lessons in the [passive-observation contract](docs/superpowers/research/evidence/jev-axi-passive-observation-2026-10-05/observation-contract.md) and the [comparison contract](.agents/skills/handling-sys1-incidents/references/comparison-contract.md).

The error investigation also shows why acquisition is insufficient: models sometimes requested relevant material while omitting its conclusion, and commit evidence was overstated as publication evidence. Record actual authored explanations and review findings, not merely retrieval counts. See [errors-investigation.md](docs/superpowers/research/evidence/jev-axi-integration-investigations-2026-10-12/errors-investigation.md).

## Outcome branches

| Observed outcome | Supported next decision |
| --- | --- |
| Inputs available before visible support-checking work, with identifiable subsequent checking | Prepare a reasoning-replacement comparison. Do not claim that work was avoided. |
| Inputs available before reuse of a claim later corrected | Prepare an independent early-check hypothesis, counting preparation, consumption, false alarms, and required review. |
| Inputs available only after support checking | Current placement does not establish replacement value. Independent-check opportunity remains separately assessable. |
| File evidence available early, committed evidence only later | Record a producer boundary/timing limitation. Consider a separately reviewed snapshot-reader proposal; no producer modification is authorized here. |
| Ordinary publication preparation repeats identifiable navigation/reconciliation | Prepare the distinct changed-text delivery comparison. |
| Ordinary handling produces a complete useful result with no identified remaining opportunity | Retain ordinary handling for this scope. One task does not establish general uselessness. |
| Window missed, source unstable, insufficient sources, absent review binding, missing costs, or budget reached | Report the precise limitation and bounded partial result. No retrospective substitute, automatic rerun, or failure attribution to the ordinary task. |
| Observer correction affects later behavior | Retain affected results and costs; do not present them as an untouched baseline. |

End at the first terminal ordinary publication-preparation result, withdrawal, workload drift, acquisition failure/limit, or time ceiling. Publication itself is outside the required observation endpoint; if independently evidenced within the window, report it separately.

## Accounting join and remaining fields

The ordinary-work/accounting lane must attach to these artifact and event identities and supply:

- Action categories separating ordinary citation/source work from observation selection, copying, hashing, packaging, refresh, interpretation, and reporting.
- Timing semantics distinguishing active effort, operation duration, wall latency, and overlapping work.
- Available usage routes and attribution rules, retaining unknown failed-attempt usage and unmeasured operator effort.
- One count for shared collection, with separate marginal consumer work.
- Terminal quality/review grading and the accepted cost priorities.

Evidence classes must remain explicit: retained artifact/tool evidence, owner report, voluntary estimate, inference, or unknown. A owner’s “already resolved” statement records their reported state; it does not establish internal reasoning or correct support. The [maintained comparison contract](.agents/skills/handling-sys1-incidents/references/comparison-contract.md) governs whole-owned accounting through failed, skipped, and terminal outcomes.

Fill at admission: acceptance identity/time; collector and permitted destinations; fresh eligibility state; checkpoint visibility route; exact future review/verification/publication artifact paths; and source-access authority. Fill only when produced: assertion text/coordinates, cited sources and digests, checkpoint commits, review candidate/results, publication comparison endpoints, and observed accounting values. These genuinely future values must not be invented.

## Procedure consumption and closure

I used `research` and `capturing-agent-procedures`, consuming the comparison procedure with SHA-256 `9f876cd27c4bd6fe82d56feabc6e31e05d029d7cac18f9651194218e2e1aa981`. This handback captures proposed executable contract text; it is not an installed convention. The coordinator must join both lanes, review the resulting contract, preserve its revision, and place its invocation pointer in the authorized execution instructions. The execution consumer loads that reviewed revision before admission and returns the event/artifact/accounting record plus the terminal branch.

All ten manifest inputs matched their hashes and byte counts before inspection and before handback: 107,479 source bytes. The frozen request digest also remained unchanged. I did not inspect the foreign workload, collect its content, edit files, access private histories, run producers/tests/models, use the network, or subdelegate.

My system context identifies a GPT-6-based Codex agent; no exact runtime model/effort attestation was available. Authority was bounded read-only preparation under the supplied standing admission. This lane’s complete owned result is the contract proposal above. Collection, execution acceptance, integration, review, admission lifecycle, and publication remain with the coordinator.