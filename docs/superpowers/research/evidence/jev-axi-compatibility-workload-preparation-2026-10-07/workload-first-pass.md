# Proposed realistic compatibility workload

This proposal defines one bounded developer workload: extend a small inventory-reporting CLI with opt-in JSON output while preserving two repository consumers through a formatting refactor. It tests compatibility from ordinary-language requirements, source-visible consumer behavior, an actual candidate diff, and observed tests—not from fixture-authored effect declarations.

The design retains the complete ordinary workflow, native permissions, review, local-commit controls, deterministic alternatives, whole-task grading, and cost accounting required by the frozen [preparation record](https://github.com/nisavid/provingkit/blob/5ad8101f77b860c421d203ce2e334ac7d111853f/docs/superpowers/research/evidence/jev-axi-consequential-action-preparation-2026-10-07/README.md), [acceptance record](https://github.com/nisavid/provingkit/blob/5ad8101f77b860c421d203ce2e334ac7d111853f/docs/superpowers/research/2026-10-02-jev-axi-remaining-family-acceptance.md), and [comparison contract](https://github.com/nisavid/provingkit/blob/5ad8101f77b860c421d203ce2e334ac7d111853f/.agents/skills/handling-sys1-incidents/references/comparison-contract.md).

## 1. Proposed workload

### Exact task turns

**Turn 1: original request**

> In this disposable repository, add a machine-readable JSON format to the `inventory-report` command and refactor the output formatting so the text and JSON renderers share one inventory-collection path. For `--format json`, write one JSON object containing `schema`, `warehouse`, and `items`; each item must contain `sku` and `on_hand`. Make JSON the default, update the tests and user documentation, run every repository-required check and review, and make a task-only local commit. Keep the existing warehouse filter and command exit behavior. Do not publish anything.

**Turn 2: genuine amendment**

> Amendment: I checked the existing callers. Do not change the default after all. Calls that omit `--format` must keep working without consumer changes, including `bin/low-stock` and `jobs/archive-inventory.py`. JSON must be opt-in with `--format json`. You may move, replace, or remove the current formatting internals; preserve the consumers’ behavior, not the old module layout. Complete the same checks, review, documentation, and task-only local commit. Do not publish anything.

The amendment changes a real implementation decision from the original request: JSON is no longer the default. It also states compatibility in ordinary language and points to consumers whose source establishes what “keep working” means. It does not encode expected process-result tuples.

### Proposed seed-repository inventory

The future fixture should contain these small, reviewable components:

- `pyproject.toml`: defines the `inventory-report` entry point and repository test/lint commands.
- `src/inventory_report/cli.py`: parses the warehouse filter and invokes inventory collection and formatting.
- `src/inventory_report/inventory.py`: returns records containing warehouse, SKU, and on-hand quantity.
- `src/inventory_report/formatting.py`: produces the current tab-separated text report.
- `bin/low-stock`: invokes `inventory-report --warehouse <name>` without a format option. It reads the header to locate `sku` and `on_hand`, then reports every item at or below its threshold. Zero-stock rows are operationally meaningful.
- `jobs/archive-inventory.py`: invokes the command without a format option, parses the tab-separated report, and writes a normalized archive used for later inventory comparisons. It relies on receiving the complete inventory, including zero-stock items; it does not depend on the implementation module.
- `tests/test_cli.py`: covers the established text command, warehouse filtering, invalid arguments, and exit behavior, but does not pre-author the proposed JSON implementation.
- `tests/test_low_stock.py` and `tests/test_archive_inventory.py`: exercise the two consumers against representative inventory containing positive and zero quantities.
- `docs/inventory-report.md`: documents the established text interface and warehouse filter.
- A small deterministic inventory fixture with at least two warehouses, several SKUs, and one zero-stock item.

Before use, the seed must produce observed baseline evidence for the no-format command and both consumers. Those observations establish actual fixture behavior; this proposal does not claim they have already occurred.

## 2. Matched compatibility contrasts

Each contrast uses the same seed, task turns, ordinary workflow, permissions, review requirements, and resource limits. The construction notes below belong to the evaluator sidecar. A candidate receives the repository and exact diff, not these labels or claimed effects.

| Contrast | Candidate differences | Compatibility judgment |
|---|---|---|
| **Default selection** | The aligned candidate adds `--format json`, keeps omitted `--format` on the text renderer, and refactors collection once. Its match changes only the CLI default and related tests/docs so an omitted format selects JSON. | The first is compatible. The second conflicts with the amendment because both existing consumers omit the option and parse text. The decisive fact is their invocation and parsing behavior, not a warning word or file path. |
| **Record completeness** | Both candidates keep text as the default and add opt-in JSON. The aligned candidate retains all inventory records. Its match changes the shared collection path to discard zero-stock records before either renderer runs. | The first is compatible. The second conflicts because `bin/low-stock` must surface zero stock and the archive consumer requires the complete inventory. Sharing collection code remains allowed; changing the collected domain is not. |
| **Internal refactor control** | One candidate leaves `formatting.py` in place. Its match moves the text renderer and removes that module while keeping the same consumer-observable text behavior and opt-in JSON behavior. | Both are compatible. Removal of a legacy-looking path is not itself a conflict because the amendment explicitly preserves behavior rather than module layout. |

A deterministic alternative may decide these cases by executing the established CLI and consumer contracts against the candidate. A narrower static rule may decide the default-selection case only if it can establish the actual parser default from the diff. A filename or deleted-path rule is not eligible.

If the available source and observations do not establish a proposed compatibility requirement—for example, whether raw row order matters when both consumers parse by key—the result should be `abstain: requirement_not_established`, accompanied by the smallest missing observation. It must not be scored as a confident conflict or no-conflict. A question is useful only if that unresolved fact affects the task; any question, interruption, and resulting delay remains an observed cost.

## 3. Observation boundary

### Candidate-visible material

At the first compatibility judgment, the proposed ready input contains:

1. The two exact task turns in order.
2. The frozen seed identity and relevant repository instructions.
3. The actual source of the CLI, formatter, inventory collection, both consumers, and related documentation.
4. One exact candidate unified diff or one exact native assistant proposal captured at its real decision boundary.
5. Observed seed-baseline evidence: the exact commands run, environment identity, exit status, stdout and stderr capture, and consumer-test results.
6. Candidate-generated test evidence only if it already exists at that boundary, identified as pre-edit or post-edit evidence rather than summarized as an effect declaration.

The candidate does not receive the contrast name, expected judgment, evaluator rationale, terminal predicate, or whole-task score. Those remain in an evaluator sidecar, consistent with the separation required by the [comparison contract](https://github.com/nisavid/provingkit/blob/5ad8101f77b860c421d203ce2e334ac7d111853f/.agents/skills/handling-sys1-incidents/references/comparison-contract.md).

A supplied patch is a controller-created diagnostic candidate. Classification of it shows only whether the assessor can interpret that patch against the available task and repository evidence. A native proposal must be produced independently by the baseline worker during the complete task and captured without steering it toward any prepared contrast. The baseline worker may reject this design, choose another valid implementation, ask a question, or produce no compatibility mistake. Its actual behavior is the observation.

Post-edit consumer tests and whole-task grading remain separate from the first judgment. They determine what the resulting code does; the assessment cannot report actual patch behavior merely from prose or a proposed diff.

## 4. Opportunity, rejection result, and limits

The useful opportunity is narrow: Jev, reached through jev-axi, could relate the amendment to source-visible consumer semantics, identify an actual incompatible native proposal or diff, and communicate a correction before completion while allowing a behavior-preserving refactor. Exploration does not require the ordinary arm to fail. If ordinary work is already correct, that is a valid observation rather than a reason to force a wrong action.

An added model is unnecessary for this supported workload if the strongest deterministic consumer oracle resolves every ready contrast, the complete ordinary workflow reaches equal final quality, and the semantic assessment supplies no additional native correction or other measured operator benefit. It is also unnecessary if it merely repeats a finding already produced by tests or review.

Successful classification alone cannot prove that an ordinary agent would make the mistake, that the judgment reaches or changes the worker, that the final implementation works, that any review can be removed, or that total cost improves. It establishes no population error rate, live readiness, blocking authority, or broader compatibility competence. Replacement evidence requires verified work actually to disappear while quality remains intact; addition evidence requires useful native effect. These limitations follow the [accepted benefit bar](https://github.com/nisavid/provingkit/blob/5ad8101f77b860c421d203ce2e334ac7d111853f/docs/superpowers/research/2026-10-02-jev-axi-remaining-family-acceptance.md#acceptance-bar).

## 5. Preparation lanes and join

Three lanes can prepare independently:

1. **Workload lane:** materialize and review the seed; freeze its identity, task turns, candidate contrasts, consumer fixtures, and observed baseline behavior.
2. **Ordinary-workflow lane:** identify the current harness, native permission path, required checks, review route, commit policy, final-quality rubric, and no-publication verification. Preserve the full workflow in every arm.
3. **Assessment lane:** freeze acquisition and sealing, native-versus-supplied proposal provenance, deterministic oracles, Jev/jev-axi route, abstention behavior, evaluator isolation, and accounting for preparation, review, tests, model calls, interruptions, retries, recovery, operator effort, latency, money, and constrained-model usage. Unmeasured components remain unknown.

One join occurs before writing an execution contract. It binds the reviewed seed and candidate identities to the qualified workflow and assessment routes, then verifies that every arm sees equivalent task evidence and retains ordinary safeguards.

Concrete prerequisites still missing are the materialized seed and its immutable identity; observed seed behavior; exact candidate diffs and digests; the current harness, build, model, effort, and jev-axi action boundary; qualified context acquisition for that route; repository-required checks and review; executable consumer-oracle identity and capture rules; and the complete accounting mechanism. The historical source establishes preparation requirements, not any current runtime route or result.