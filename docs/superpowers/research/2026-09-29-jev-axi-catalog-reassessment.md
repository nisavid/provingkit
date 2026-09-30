# Catalog coverage and earlier dispositions

The incident effort did not qualify the full `jev-axi` hook catalog under the later whole-workflow assignment criteria. Its results remain evidence for the bounded questions it tested.

## Terms and evidence boundary

`jev-axi` is the integration. It constructs inputs, calls Jev, interprets answers, and implements hook behavior. Jev is the separate service it uses. A defect or policy in one must not be attributed to the other without evidence.

This audit reads `jev-axi` source at `a1fe6190c65b528ad5b85cbe276fd4b68bdeb236` and retained Provingkit evidence at `aca02f1dc55928b349b3b6c5455b9b19a246aa72`. The [prior source closeout](https://github.com/nisavid/provingkit/issues/304#issuecomment-5902208142) records that the merged tree at `fb31e716d70ea92039c8b2d48524b69496b54274` matches that reviewed source; this audit did not independently read the merged commit object. It runs no model, hook, native experiment, installation, or live reconfiguration. Two independent factual passes inspected the source catalog and the decision chronology. Coordinator spot checks confirmed the supervision branches and live tracker state.

## Catalog

| Hook family | Behaviors that require separate accounting | Prior comparative coverage |
| --- | --- | --- |
| SessionStart | AXI SDK context injection, readiness/configuration information, adapters and installation | Configuration observations; no comparative benefit qualification |
| PreToolUse | Deterministic screening, context construction, six Jev questions, thresholds, permission output, failure policy | Incident diagnosis, conditional/recovery studies, and one bounded authorization comparison |
| PostToolUse | Event retention and baseline capture, context extraction, cadence, progress/stuck/off-track/needs-human questions, verdict precedence, notes and quiet logging | Mandatory-note comparison; retained behavior regression checks; limited native and alpha evidence |
| Stop | Job/diff/output construction, completeness/requirements/tests/verification questions, thresholds, warning/block/silent/skip branches | Bounded regression and native observations; no comparative utility qualification |
| pre-commit | Deterministic credential scan, diff assessments and aggregation, warning/block/skip policy | No comparative assignment evaluation identified in the incident effort |
| commit-msg | Deterministic convention check, message/diff assessments, used and unused answers, warnings/strict behavior | No comparative assignment evaluation identified in the incident effort |
| pre-push | Range selection, migration/sensitivity/generated-file/leftover assessment, thresholds, deduplication and failure behavior | No comparative assignment evaluation identified in the incident effort |

Cross-cutting concerns include native delivery, installation/matcher coverage, cache behavior, usage accounting, truncation and redaction, logging failure, and supported versions. These affect both reliability and cost; they are not additional Jev classifiers.

Source anchors: [`hook.ts`](https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/commands/hook.ts), [`safety.ts`](https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/safety.ts), [`supervise.ts`](https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/supervise.ts), [`questions.ts`](https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/recipes/questions.ts), [`githooks.ts`](https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/commands/githooks.ts), and [`meta.ts`](https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/commands/meta.ts). SessionStart behavior also depends on locally resolved `axi-sdk-js@0.1.12`; its dependency source was inspected, but native consumption was not exercised in this audit.

## Earlier dispositions against the later criteria

- **Remove the mandatory needs-human note:** supported on the supplied and missing-input tasks by comparisons against omission. Injected scores isolate the effect of the instruction; they do not qualify Jev classification accuracy. The narrow conclusion is consistent with declining an optional intervention that demonstrated harm without an observed benefit in those cases. It is not proof of universal equivalence.
- **Retain supervision assessment, scoring, logging, and other interventions:** preserved and partly regression-tested, but not justified as ongoing assignments by comparative benefit and complete cost evidence. For example, `meaningful_progress` does not affect the verdict, and a high `needs_human` score still takes precedence over steering even when escalation output is quiet. Both are source facts, not proof that either behavior is useful or useless.
- **Retain Stop and SessionStart; preserve operational disables:** recorded configuration and scoped preservation are not comparative assignment decisions. Earlier mitigation and rollout acceptance retain their own limits.
- **Decline added authorization classifiers:** explicitly selected under the later contract for the fixed creation/proposal workflow. All sixteen native episodes met the case bar; none offered an unauthorized native proposal for the extra checks to catch. Complete costs remained unknown. The result supports declining those additions for that workflow, without a general economic or safety-equivalence claim.

Evidence: [supervision wording comparison](https://github.com/nisavid/provingkit/blob/aca02f1dc55928b349b3b6c5455b9b19a246aa72/docs/superpowers/research/2026-09-26-sys1-supervision-wording.md), [added-value comparison](https://github.com/nisavid/provingkit/blob/aca02f1dc55928b349b3b6c5455b9b19a246aa72/docs/superpowers/research/2026-09-26-sys1-supervision-added-value.md), [built correction](https://github.com/nisavid/provingkit/blob/aca02f1dc55928b349b3b6c5455b9b19a246aa72/docs/superpowers/research/2026-09-28-sys1-built-correction.md), [alpha decision](https://github.com/nisavid/provingkit/issues/264#issuecomment-5883383364), and [whole-workflow selection](https://github.com/nisavid/provingkit/issues/289#issuecomment-5901273214).

## Transfer of criteria

The [accepted whole-workflow contract](https://github.com/nisavid/provingkit/issues/290#issuecomment-5889881992) supplies reusable principles: distinguish replacement from addition; provide appropriate context before judgment; compare ordinary behavior, deterministic alternatives, and omission; measure complete workflow effects and costs; keep unknowns explicit. Its withdrawal/excluded-destination case requirements were for authorization checks. Other behavior families need purpose-specific reliability and benefit requirements before experiments.

Regression evidence establishes preserved mechanics. Assignment evidence establishes whether a behavior earns its place. Missing assignment evidence is neither proof of benefit nor proof of uselessness. Joint effects, shared context, and batched assessments prevent treating every score as an economically independent unit.

## Tracker scout

The completed [incident map](https://github.com/nisavid/provingkit/issues/229) and all thirteen children remain closed. No existing catalog-wide qualification ticket was found among the 256 issues listed in the live scout.

[Evaluation scoping](https://github.com/nisavid/provingkit/issues/251) owns cross-harness/model/effort/grader policy. [Agent-policy construction](https://github.com/nisavid/provingkit/issues/200) owns reusable policy construction and its seed policies. [Auto-mode classifier correction](https://github.com/nisavid/provingkit/issues/165) concerns a native harness classifier, not the `jev-axi` catalog. These are related owners, not evidence that their entire maps must block this audit.

I accepted a successor map for evidence-backed assignments across the full `jev-axi` hook catalog, revisiting earlier dispositions under the later criteria. The next decision sets purpose-specific claims, acceptance requirements, and comparison order. Current live changes and upstream submissions keep their existing approval boundaries; this audit changes neither.
