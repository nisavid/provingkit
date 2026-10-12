# Observe when a research claim is ready for an early check

Follow one assertion in an ordinary research report from its first saved draft
through review and publication preparation. Establish whether adequate evidence
is available early enough to make a narrow System One check worth comparing,
and what preparing that evidence adds to the work.

This is a proposed observation contract for
[Freeze the prospective claim-readiness observation contract](https://github.com/nisavid/provingkit/issues/585).
It requires Ivan's separate execution acceptance. It runs no Jev or other model
comparison, delivers no checking hint, changes no live configuration, and removes
no ordinary review. Jev is the assessment service; `jev-axi` is an integration
that uses it.

## Named workload and prospective boundary

The workload is [Assess System One capabilities for portfolio qualification](https://github.com/nisavid/provingkit/issues/548),
branch `ivan/research/peer-portfolio-sys1-548`, beginning at
`61b99e73ebedf8afb33b28a531daea8089504394`. Its report is
`docs/superpowers/research/2026-10-12-system-one-portfolio-capabilities.md`.
The selected section is its capability/source/evidence table and accompanying
claims about what each mechanism can and cannot prove.

The owner confirmed during preparation that this report and section were still
unwritten and unreviewed. The ordinary process saves the returned first draft,
hashes it, and freezes it before independent review. Review results and their
input manifest naturally live in that task's evidence directory. These are
owner-reported workflow facts, not observed execution or a request for an extra
checkpoint. The private binding identifies the worktree and evidence root.

Before requesting acceptance, and again immediately before collection, obtain
current metadata confirming the task, branch, base ancestry, report path, and
that its first saved draft has not yet passed into review. Record current HEAD
separately; ordinary forward commits are expected. No report content is read for
this check. If the checkpoint has passed, the owner cannot establish its state,
or the workload changes, record a missed or unestablished opportunity and stop.
Do not reconstruct an earlier checkpoint or substitute a workload. The author
continues without waiting.

At the first ordinary saved draft, select the first material, externally
checkable assertion in the named section's document order, including table
cells. A material assertion concerns a mechanism's capability, limitation, or
what its evidence establishes. Exclude headings, questions, plans, and bare
links. Preserve the complete assertion, enclosing row or paragraph, coordinates,
and ordinary citations before assessing support. Do not select a known defect,
inject an error, split a compound claim to improve its score, or skip an awkward
first assertion. No citation, more than two necessary sources, and inseparable
compound meaning remain input limitations. Keep this assertion's identity through
revision or deletion.

## Permitted evidence and collection

The System One coordinator collects local copies. No private chat/session
history, general transcript importer, directory crawl, new hook, model request,
or new collector is included. Collection uses bounded ordinary file reads and
named Git blob/diff reads, with limits checked before each read. The private
binding is reviewed alongside this contract and fixes permitted roots and the
new output directory. Existing results are never overwritten.

| Evidence | Selection and limit |
| --- | --- |
| Report | At most three complete UTF-8 copies of the named report, 256 KiB each |
| Claim sources | One or two complete source artifacts already retained by ordinary work and cited by the selected assertion, 128 KiB each |
| Review and publication records | At most four complete ordinary artifacts, collectively 1 MiB: the owner-identified input manifest, its directly referenced review result or consolidated findings, and a verification/publication-preparation record or bounded candidate diff |
| Usage and timing | At most one existing owner-identified task export, 256 KiB; absent export means unknown |

There are at most ten workload-artifact captures, 8 MiB gross content reads,
and 2 MiB retained workload content. Repeated reads, hashing reads, and Git output
charge the read pool. The event ledger and identity manifest together have a
separate 256 KiB ceiling. Stop before an indivisible read exceeds a limit; never
truncate silently. Metadata-only checks and owner coordination are also counted
as operations and effort, although not workload-content bytes.

Source artifacts must be inside the named task worktree or its named evidence
root, be regular files or existing regular Git blobs, and correspond to an
ordinary citation. Do not follow symlinks outside those roots, retrieve missing
web pages, discover replacement sources, or read arbitrary files linked by
review prose. The owner identifies the review manifest and optional export;
only its bounded direct evidence references within the permitted roots are
eligible. Future filenames and hashes are recorded when ordinary work produces
them; this rule does not authorize an unrestricted search.

The collector may use up to four metadata-only coordination/status checks to
learn when the ordinary checkpoints occur. Read at most 32 immediate filenames
and file metadata in the bound review directory to match an owner-identified
record; do not recurse. No recurring monitor or waiting process is installed.
An existing ordinary notification can trigger a capture, but no new worker
message or extra checkpoint is required. If the collector misses the first
pre-review draft, stop rather than calling a reviewed draft the initial one.

The collection window is 30 minutes elapsed wall time after successful
execution admission, including pauses. End earlier on withdrawal, workload
drift, acquisition failure, exhausted limits, or the first ordinary
publication-preparation outcome. There are no acquisition retries or substitute
workloads. After collection closes, permit ten minutes to reconcile the retained
records and write the observation handback; that interval admits no new workload
reads. Preserve partial results and any overrun, without claiming timely
completion. Neither clock stops the ordinary task.

## Checkpoints and source identity

1. **First saved draft, before review starts.** Capture the report and the
   selected assertion's existing sources. Require ordinary checkpoint metadata
   identifying the saved draft and its digest. Verify that digest against the
   captured bytes and that the review-start ordering is established; otherwise
   stop with an unstable or unordered checkpoint.
2. **Ordinary review result and revision.** Capture one natural post-review
   report version and the available bound findings. Preserve missing rounds as
   gaps rather than collecting every intermediate draft. A review must identify
   the candidate it covered before it can support a review/claim association.
3. **Publication preparation.** Capture the terminal report and eligible
   ordinary reconciliation record or diff. Record actual comparison endpoints,
   changed text, and which evidence the explanation uses. A candidate is not an
   observed push. Publication itself is not required for this endpoint.

For each acquisition, record path, byte count, SHA-256, UTC observation time,
ordinary checkpoint identity, current HEAD, and committed-versus-working-file
status. Compare file identity/size/mtime before and after the bounded read and
check any ordinary frozen digest. A concurrent change or mismatched digest ends
that capture without retry. Metadata checks alone are not proof against every
possible concurrent rewrite; the ordinary frozen digest supplies the stronger
candidate association where available. Keep observation time separate from
source occurrence/acquisition time, which can remain unknown.

Maintain three separate conclusions:

- Exact draft and evidence bytes are **available for observation**.
- Their commits, paths, digests, and coordinates meet the **existing producer's
  input requirements**.
- Their referents and contents are **adequate to examine the assertion**.

The current [claim producer](../jev-axi-comparison-producers-2026-10-07/claim_producer.py)
requires committed draft/source blobs and caller-selected evidence. A file
snapshot does not qualify that reader. Run neither producer in this observation
and request no extra commit. Determine compatibility from the retained identities
and the documented boundary; do not claim a successful producer invocation.
The [coverage producer](../jev-axi-comparison-producers-2026-10-07/coverage_producer.py)
also does not establish review sufficiency or an actual outgoing push range.

## Ordinary work and complete accounting

The baseline is the owner's ordinary authoring, source selection, citation,
support explanation, revisions, required review, and publication preparation.
Observation can influence this work. Record author/reviewer awareness, requests,
overlap, and any ordinary correction prompted by the observation. Do not withhold
a necessary ordinary correction to preserve a baseline; mark affected later work.
Do not send an observer-created support judgment or package to the author.

Use one ledger with event identity, assertion/version identity, actor, purpose,
observed and source time, artifact references/digests, evidence basis, attempt
identity, state/outcome, bytes, operations, elapsed interval, available usage,
valuation/cost source, shared-cost identity, gaps, and interference. Each value
is measured, owner-reported, estimated, inferred, or unknown; null is not zero.
Record separate buckets for:

- Ordinary authoring/source work and subsequent reuse/revision.
- Study-specific assertion selection, retrieval, copying, hashing, and packaging.
- Collection, interpretation, and reporting overhead.
- Required review, failed or stale reviews, corrections, and re-review.
- Operator interruptions and any naturally performed checking.
- Publication reconciliation and unobserved work.
- This study's preparation/review costs, outside the observed ordinary task.

A source access does not prove comprehension; an absent action record does not
prove no work occurred. Do not infer internal thought or exact active effort
from elapsed time. Include failed, cancelled, unused, and incomplete work when
its records are available. Count shared production once in combined totals;
show consumer-specific interpretation separately. Do not amortize across hoped-for
future reuse. Report observed subtotals, never complete task totals from partial
records.

Use only the admitted existing usage export for ordinary task tokens. Preserve
reported input, cached input, output, and reasoning counts with attempt identities
and counter semantics. Sum only compatible per-response counters; cumulative
deltas require matching lineage and valid endpoints. No export or undocumented
semantics means unknown usage. For supported counts, report API-equivalent value
only when the export supplies an identified rate schedule and its effective date,
model/cache/reasoning treatment. Otherwise report unpriced tokens and the missing
rate binding; perform no extra API or billing read. Actual cost and quota effects
remain unknown without attributable evidence. API-equivalent value is not a bill.
Observer/preparation usage, where separately available, stays in its own account.

Record readiness-to-review/reuse intervals, tool duration, collection wall time,
and any voluntary active-time estimate separately. Do not add overlapping
intervals into elapsed task duration. One brief optional operator record may be
requested only if Ivan naturally checks this outcome: approximate active time,
what he consulted/repeated, and whether he could make the intended decision.
Count that reporting effort; no answer remains unknown and does not delay closure.

## Grading and the decision this can inform

After closing acquisition, reconcile the selected assertion, its evidence, edits,
and bound ordinary review findings. Record whether complete referents and evidence
were available; then classify the retained assertion as supported, unsupported
extension, contradicted, unresolved conflict, or ungradeable, with cited evidence.
Missing evidence is not a contradicted claim or a model failure. This is the
coordinator's evidence assessment, not an independent model benchmark. Preserve
disagreement with ordinary review instead of declaring that review an oracle.

| Observation | Permitted conclusion and next preparation |
| --- | --- |
| Adequate inputs precede identifiable remaining support-checking work | Prepare a replacement comparison naming the work it would remove; no savings established |
| Inputs precede reuse/review, including after an author judgment | Preserve a possible independent-checking benefit; prior judgment alone does not make another check useless |
| Later ordinary review corrects an overstatement after an earlier adequate checkpoint | Prepare an earlier-detection hypothesis, retaining observed propagation/rework; no evidence that Jev would prevent it |
| Study preparation repeats the proposed replacement work, or commits arrive too late | Current placement lacks replacement evidence; consider a distinct checking purpose or a separately reviewed snapshot-reader proposal |
| Ordinary publication repeats evidence navigation | Consider the separate deterministic-delivery comparison |
| No concrete remaining opportunity appears | Retain ordinary handling for this observed scope; one case does not establish general uselessness |
| Order, sources, review, or costs are unavailable | State the exact gap and which conclusion it prevents; do not start another observation automatically |

This passive episode estimates neither frequency nor intervention benefit,
calibration, or economic superiority. A later semantic comparison would keep
Jev, Decisions, Luna 6 Low/Medium/High, and Sol 6.1 Low eligible. A later native
comparison would retain ordinary handling, deterministic preparation, omission,
required review, final quality, false interventions, and complete costs. Neither
comparison is authorized by accepting this observation.

## Completion and procedure consumption

The executing coordinator loads this reviewed contract and the unchanged
[`handling-sys1-incidents` comparison procedure](https://github.com/nisavid/provingkit/blob/5be38ce96e36b08d017fc1e2cfb5bcf9ff606d03/.agents/skills/handling-sys1-incidents/references/comparison-contract.md)
before admission. Retain their identities, acceptance, eligibility checks,
artifact manifest, event/accounting ledger, terminal reason, gaps, and supported
next decision. Every planned checkpoint and cost bucket needs a result or an
explicit unknown. Missing order prevents an early-opportunity claim; missing
review prevents a final-quality claim; missing usage prevents a complete economic
claim. A complete handback may accurately report those limits.

This observation-specific proposal consumes existing equipment. It installs no
shared method or convention. The [joined investigations](../jev-axi-integration-investigations-2026-10-12/README.md)
explain its System One integration purpose; the preparation record preserves both
independent proposals and the coordinator's choices.
