# Evidence for the whole-workflow Sys1 comparison

This collection lets a reviewer trace the bounded recommendation to synthetic inputs, native effects, reported costs, and the source used to collect them. Start with the [readout](../../2026-09-29-sys1-whole-workflow-comparison.md).

- [Native observations](native-observations.json) contain sixteen selected episodes and two invalid attempts, identified by batch and case. Select r4/n01–n05 and r5/n06–n16 for the comparison; retain r3/n01 and r4/n06 as failed instrumentation costs.
- [Retained proposals](retained-proposals.json) contain twelve initial proposals and sixteen terminal-history proposals, each across four arms. They are conditional judgments without native effects. Labels are evaluation data and did not enter candidate requests.
- [Experiment identities](experiment-identities.json) preserve normalized manifests and original manifest hashes, including source, input, label, configuration, model, permission, and policy bindings. [Source identities](sources/identities.json) distinguish original and normalized archival bytes and the instrumentation revisions.
- [Protocol](protocol.md) is the final preparation document, including the reviewed timing/path deltas. Its preparation-time “unverified” fields remain historical; observed outcomes belong in the readout and records.
- [Preflight reviews](preflight-reviews.json) retain clean and nonclean preparation reviews. Their bindings and input checks are cooperative coordinator observations, not signed or portable attestations.
- [Model-free checks](model-free-checks.json) retain red/green output, including accounting, role attribution, fixture containment, and corrected timing/path branches. These tests do not qualify production authority or unseen native behavior.
- [Setup inventory](setup-attempts.json), [qualification observations](qualification-observations.json), [qualification accounting](qualification-accounting.json), and [reported counter events](qualification-reported-counters.json) retain preparation outcomes and measurement gaps.
- [Procedure consumption](procedure-consumption.json) records the unchanged reviewed incident procedure and context/accounting prerequisite. [Factual adjudication](native-factual-adjudication.json) records the bounded final-reply and native-call inspection.

## Projection and reproduction limits

These are public projections of task-owned synthetic experiments. Host paths are replaced with named placeholders; original artifact hashes identify the retained private bytes. Raw native transcripts, hidden reasoning, startup/developer/system text, authentication, and complete host configuration are omitted. Task messages and actual assistant/tool text needed to judge these synthetic approvals are retained with their origins. Two source copies also remove trailing line whitespace and extra terminal blank lines, as recorded in their identity entries. Normalization changes the published hashes, so a normalized file is not proof of the original bytes. Original hashes and published source hashes are separate fields.

Source files end in `.txt` to identify archival evidence, not an installed runtime or reusable runner. They depend on the pinned local Jev build, particular native versions, and experiment bindings. Do not execute these normalized copies as a live hook. Reproduction requires a fresh qualified preparation and review; replaying an old reservation or replacing paths is not sufficient.

No complete billing or account-quota measurement is supplied. Native counters are observed-only, and failed/missing counters remain unknown. Per-turn, cumulative, per-hook, and episode measurements overlap; the readout states which quantities can be summed. Claude list-price fields are retained as observations, not actual charges.

Native processes completed and terminated. Synthetic fixtures and original private records remain retained locally for audit. No live rollout or upstream submission is part of this collection.
