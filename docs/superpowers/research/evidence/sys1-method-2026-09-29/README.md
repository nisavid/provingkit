# Whole-workflow method evidence

This evidence supports the repo-carried `handling-sys1-incidents` intake aid at `23c3f865f36aa3c727d33cf6d10fab3c1967a5d0`. The numbers in the [case requests](cases.json) are authored test data, not measurements of the four Sys1 workflows.

- [Consumer results](consumer-results.json) preserve five native worker responses, requested model and effort, input hashes, original response hashes, and fixture-path normalization. Each application worker was a fresh child with no parent conversation. The separate ENOSPC worker tested one negative routing case.
- [Frozen grading criteria](grading-contract-r1.json) define the initial application checks. Independent review added maintenance/amortization and per-case/per-harness reporting checks; their results and limits are in [review and validation](review-and-validation.json).
- [First reference draft](r1-comparison-contract.md.txt) and [second reference draft](r2-comparison-contract.md.txt) preserve failed candidates. The final reference is the [maintained source](../../../../../.agents/skills/handling-sys1-incidents/references/comparison-contract.md); the prior baseline is available at [the prerequisite revision](https://github.com/nisavid/provingkit/blob/81415d50772b7a8d008bb68d30e3751ce823e81d/.agents/skills/handling-sys1-incidents/references/comparison-contract.md).

The prior skill already led its consumer to request context and cost evidence and choose ordinary harness behavior in the supplied screen. These observations do not establish behavioral improvement, automatic triggering, complete amortization handling, or autonomous incident adjudication. They do not choose a correction for the actual incident.

The [downstream invocation](downstream-invocation.json) starts from repository `AGENTS.md`, locates the published procedure, records its source hashes and revision, and returns the comparison prerequisites without executing the experiment.
