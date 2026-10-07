# Compatibility workload and baseline preparation

This proposal prepares a small inventory-report migration for comparing complete ordinary development, explicit behavioral comparison, and a possible semantic assessment. The next useful artifact is a working seed with real consumer behavior and a reviewable observation contract. No workload episode, Jev request, role assignment, or live change has been qualified by this preparation.

Two independent Daybreak research peers developed the [workload](workload-first-pass.md) and [baselines](baselines-first-pass.md) from the same frozen public sources. Their first handbacks are retained unchanged. The proposal below joins them under the [accepted family purposes](../../2026-10-02-jev-axi-remaining-family-acceptance.md) and the [whole-workflow comparison contract](../../../../../.agents/skills/handling-sys1-incidents/references/comparison-contract.md). It resolves their differences for preparation; the handbacks are research inputs, not additional requirements.

## Proposed task and supported consumers

Use a disposable Python repository containing an `inventory-report` command, a low-stock consumer, an archive consumer, tests, documentation, and a small inventory fixture. Both consumers invoke the command without a format option and parse its existing tab-separated output. The low-stock consumer includes zero-stock items. The archive consumer preserves every inventory record. The fixture represents two warehouses, positive and zero quantities, and empty results. Add spaces or non-ASCII values only if the seed supports them and they serve a stated consumer case.

The proposed ordinary-language requests are:

> In this disposable repository, add a machine-readable JSON format to the `inventory-report` command and refactor the output formatting so the text and JSON renderers share one inventory-collection path. For `--format json`, write one JSON object containing `schema`, `warehouse`, and `items`; each item must contain `sku` and `on_hand`. Make JSON the default, update the tests and user documentation, run every repository-required check and review, and make a task-only local commit. Keep the existing warehouse filter and command exit behavior. Do not publish anything.

> Amendment: I checked the existing callers. Do not change the default after all. Calls that omit `--format` must keep working without consumer changes, including `bin/low-stock` and `jobs/archive-inventory.py`. JSON must be opt-in with `--format json`. You may move, replace, or remove the current formatting internals; preserve the consumers’ behavior, not the old module layout. Complete the same checks, review, documentation, and task-only local commit. Do not publish anything.

These are proposed synthetic task turns. The execution contract must specify their delivery boundary. Delivering both before work begins tests reconciliation of ordered requirements; it does not establish recovery from a mid-task amendment. A later amendment must have a retained actual delivery event and a bounded ordinary opportunity, without forcing an incorrect action. A missing opportunity remains a result.

Before a runnable contract, settle the JSON schema version, warehouse representation when no filter is supplied, supported SKU and quantity types, and empty-result behavior in the fixture specification. These ordinary fixture choices belong to preparation; unresolved experiment scope or stakeholder trade-offs return to the operator. Do not make graders invent missing requirements after seeing results.

## What the preparation should distinguish

The first contrast changes the default renderer while keeping the JSON addition otherwise comparable. The amendment and consumers establish why an omitted format must still select text. The second contrast drops zero-stock records in the shared collection path; it can break both consumers even though the output format remains correct. A third contrast moves or removes formatting internals while preserving public behavior. Both versions of that third contrast should remain acceptable.

The workload author must materialize actual patches and derive their effects from source and observed behavior. The descriptions above are construction proposals, not declarations that a particular implementation has those effects. Candidate inputs receive neutral identifiers, task turns, source, patch, and available evidence. Construction notes, expected answers, and grading labels remain separate.

These constructed contrasts can test discrimination and integration. They cannot demonstrate that ordinary development would produce a defect. Native work must be allowed to produce correct code, choose another valid design, ask a necessary question, or reveal no useful intervention opportunity.

Compatibility covers documented or consumer-supported behavior. It does not freeze every old implementation detail. Specify exact output bytes only where an actual consumer or contract requires them; use semantic comparison elsewhere. If row order is irrelevant to the consumers and unspecified by the contract, a reordered report is not a defect. An unavailable observation or unresolved material requirement cannot count as a pass or a confident conflict.

## Baselines and useful effects

The ordinary arm keeps discovery, implementation, developer-authored tests, required checks and independent review, correction, local commit, and native permissions. It may discover consumers and build effective tests without special prompting. Do not disable that work to create a role for Jev.

The behavioral-comparison arm retains ordinary work and adds an explicit pre-edit/post-edit comparison of supported CLI and consumer properties. Its diagnostics are agent-visible and its construction, execution, diagnosis, correction, and maintenance costs belong to that arm. The final grading oracle is separate, applies to every arm, and withholds its answers until the relevant work is finished. A hidden oracle is not free assistance for one arm.

A semantic assessment remains an eligible later comparison, not a prerequisite for materializing the seed or observing ordinary work. Its delivery could use `jev-axi`, an ordinary review point, or another supported placement within the accepted catalog scope. Jev is the assessment service; `jev-axi` is one integration. The chosen placement and context must be qualified before that arm runs.

An early advisory could help in either of two ways: correct a consequential mistake that ordinary work leaves unresolved, or reduce the complete work needed to reach the same quality. The latter can remain useful even when a later ordinary review would catch the defect. Measure the displaced diagnosis, editing, reruns, and review work; an earlier warning alone establishes no saving. A proposed replacement must identify and actually remove the named review work. Operator checking benefit remains a separate outcome with a named consumer and measured effort.

No extra false steering, redundant stops, unnecessary questions, or reduced quality is permitted under the accepted initial bar. Passing constructed classifications alone establishes neither native benefit nor economic superiority. Keep omission eligible when ordinary work or behavioral tests suffice and an added assessment shows no useful effect after all costs.

## Parallel preparation and join

Three preparation lanes can proceed concurrently after agreeing on the task turns and supported interfaces:

1. Materialize the seed and actual consumer scenarios. Record observed baseline commands, exit status, stdout, stderr, environment, and test results. Prepare matched patches with neutral identifiers and a separate construction record.
2. Specify complete ordinary development and the explicit behavioral comparator. Separate stable, intentionally changed, and unspecified properties. Identify required checks, independent review, local-commit handling, and the final oracle. Consumer tests that already belong to the seed must remain available equally; added diagnostics and hidden grading remain distinct.
3. Prepare acquisition and accounting for the proposed observation. Bind current requirements, source, candidate, and evidence to the actual judgment boundary. Record every attempt and include preparation, tests, review, false warnings, recovery, operator effort, timings, tokens, equivalent API-rate value, and observed charges or subscription use where available. Preserve unknowns and allocate shared preparation explicitly.

Join before freezing the execution contract. Resolve mismatched consumer assumptions, prove that the retained inputs support the judgments being graded, verify that ordinary inspection is meaningful within the proposed limits, and keep model route work conditional on the arms actually proposed. No model route or assessment service is required merely to build a local fixture.

The resulting contract should state whether the first accepted episode observes ordinary development alone or includes an explicit behavioral comparison, and whether it uses supplied patches, a native task, or separate phases. Keep those claims distinct. A later model comparison needs a concrete remaining hypothesis; ordinary success is evidence, not a reason to manufacture failure.

## Completion boundary

This research supplies a proposed workload, meaningful contrasts, baseline design, and preparation join. The seed, actual patches, executable comparator, current observation route, and execution contract are still to be built and reviewed. The contract must return for execution acceptance. Existing upstream-submission and live-change holds remain in place.
