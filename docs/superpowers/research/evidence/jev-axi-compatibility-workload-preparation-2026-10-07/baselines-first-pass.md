# Compatibility baseline for an inventory CLI migration

This proposal freezes one bounded developer workload and preserves ordinary implementation, review, permissions, and tests as the primary baseline. A behavioral comparison is an added option, not a substitute for ordinary reasoning. Jev is considered only through a later, qualified jev-axi advisory arm.

## 1. Proposed workload and baseline workflows

### Bounded candidate

**Proposal:** Use a disposable repository containing a small inventory-report CLI and at least one existing script that consumes its default output.

The ordinary-language task has two turns:

1. Add a machine-readable JSON output option and refactor the formatting code. Update tests and documentation, run the repository-required checks, obtain the required review, and make a local task-only commit. Do not publish.
2. Amendment: existing scripts must continue to work without changes. Preserve the default command’s public behavior; JSON is an additional format, not a replacement.

The prompt deliberately does not dictate old output bytes. Those should be discovered from the frozen seed, its documentation, tests, consumers, and observed behavior. The proposed change must be an actual patch, and compatibility must be judged from that patch or its observed behavior rather than a fixture-authored list of claimed effects.

A useful matched contrast within this one workload is:

- an actual patch that accidentally changes a supported aspect of the default interface while adding JSON; and
- an actual patch that performs the same requested refactor and JSON addition without that change.

These are constructed cases, not evidence that an ordinary agent would produce either patch. They can qualify assessment and integration mechanics, but prevention requires a complete native task in which the ordinary workflow actually leaves a relevant defect for an added assessment to correct ([acceptance bar](https://github.com/nisavid/provingkit/blob/5ad8101f77b860c421d203ce2e334ac7d111853f/docs/superpowers/research/2026-10-02-jev-axi-remaining-family-acceptance.md#acceptance-bar)).

### Workflow A: complete ordinary baseline

1. Receive both ordinary-language turns and inspect the frozen repository.
2. Identify the CLI’s documented interface, existing tests, and actual in-repository consumers.
3. Establish which observed default behaviors those sources make compatibility obligations.
4. Implement the JSON option and refactor.
5. Add or update developer-authored tests for the requested behavior.
6. Run every check required by the repository and selected execution profile.
7. Conduct the required review of implementation, tests, and documentation.
8. Revise and repeat affected checks and review until the applicable review requirement is met.
9. Make the permitted local task-only commit and verify that no publication occurred.
10. Grade the final task independently against the frozen compatibility and quality contract.

This is already-required work: understanding the amendment, inspecting consumers, implementing, testing, documenting, reviewing, committing, and preserving native permissions. No ordinary reasoning is removed merely because another assessment is present. That follows the source requirement that the omission arm retain ordinary harness behavior, permissions, checks, review, and whole-task grading ([migration omission workflow](https://github.com/nisavid/provingkit/blob/5ad8101f77b860c421d203ce2e334ac7d111853f/docs/superpowers/research/evidence/jev-axi-consequential-action-preparation-2026-10-07/README.md#migration-omission-and-whole-task-rubric)).

### Workflow B: ordinary baseline plus explicit behavioral comparison

Workflow B retains every step above. It adds:

- a pre-edit capture of selected public command behavior from the frozen seed;
- the same command observations after editing;
- comparison under a pre-frozen rule appropriate to each property;
- delivery of any mismatch to the developer as an explicit diagnostic;
- correction, repeated tests, and renewed review when the patch changes; and
- accounting for capture, comparison, interruption, diagnosis, reruns, and recovery.

The behavioral comparator is not necessarily byte-for-byte everywhere. Exact bytes are appropriate only where documentation, tests, or a real consumer establish them as stable. Semantic comparison is appropriate where, for example, record meaning is stable but incidental whitespace is not. Unsupported or incompletely captured behavior yields “unavailable,” not compatibility.

## 2. Observation contract

### Stable compatibility obligations

The future contract should observe these properties only where the seed establishes them:

- accepted default invocation and options used by supported consumers;
- process exit status;
- stdout and stderr separation;
- output bytes, delimiters, ordering, and final newline where a consumer or declared contract depends on them;
- inventory record meaning and inclusion rules;
- behavior for the frozen empty and populated inventories;
- supported error behavior exercised by an existing consumer or contract; and
- continued success of the identified existing scripts without modification.

The workload author should freeze three consumer scenarios:

1. **Populated inventory:** the default invocation is consumed by an existing script from the seed.
2. **Empty inventory:** the default invocation and the new JSON option both return their specified empty-result behavior.
3. **Representative values:** one seed-supported record includes the most demanding value already supported by the CLI, such as spaces or non-ASCII text, if such support is established.

Exact expected observations come from the seed capture and contract analysis, not from prose invented for the experiment.

### Intentionally changed behavior

The new JSON option may introduce:

- a new accepted argument or option value;
- a documented JSON schema;
- JSON-specific ordering or formatting rules; and
- format-specific errors for invalid requests.

These are judged against the new requirement and documentation, not against old default output.

### Unspecified behavior

Internal formatter organization, helper names, and retention of a particular adapter or module are not compatibility obligations unless the seed exposes them as a supported interface. Timing, memory use, terminal decoration, locale behavior, and unexercised error cases also remain unspecified unless the workload author supplies evidence that they belong to the supported contract. Existing behavior alone does not make every detail permanent.

## 3. Falsification, limits, and label isolation

A compatibility claim is falsified if any frozen stable property differs in the candidate, an identified consumer fails, the default invocation starts emitting JSON, output moves between stdout and stderr, or a requested JSON result violates its frozen schema or record semantics. Launch failure, timeout, incomplete capture, or an uncontrolled environment makes the observation unavailable rather than a pass.

Passing establishes only that the selected patch met the frozen obligations for the supported commands, fixtures, environment, and consumers. It does not establish compatibility for every input, platform, external script, or future version. Nor does it show that the ordinary agent would have made the defective patch, that Jev prevented it, or that the intervention has a population error rate. One episode supports a bounded observation, not general equivalence ([comparison contract, observations and limits](https://github.com/nisavid/provingkit/blob/5ad8101f77b860c421d203ce2e334ac7d111853f/.agents/skills/handling-sys1-incidents/references/comparison-contract.md#comparison-contract)).

The evaluator sidecar should hold opaque case roles, expected compatibility outcomes, and hidden grading labels. Candidate inputs contain the ordinary task, repository, and actual patch or behavior, but no “regression” label or expected answer. Ordinary reviewers receive the task, patch, normal repository evidence, and developer-authored tests; they do not receive hidden labels or the evaluator’s expected finding.

The independent grading oracle is run for every arm. It must not become free help for one candidate: its hidden results are withheld until the arm’s ordinary work and any selected intervention finish. If an agent-visible behavioral comparator is itself an intervention, only that arm receives its diagnostic, and all preparation, execution, interruption, and recovery costs are charged to it. Shared oracle construction is recorded as one-time research work and allocated explicitly. Arm-specific tailored tests remain arm-specific costs; they cannot be retroactively added only after seeing which arm failed.

## 4. Minimal useful comparison

Before preparing a Jev assessment, establish:

1. the frozen seed and supported compatibility contract;
2. actual patch bytes for the defective and preserving contrasts;
3. the complete ordinary workflow and whether it detects and corrects the defect;
4. the explicit behavioral comparator’s result and cost;
5. the actual context jev-axi can deliver to Jev before judgment; and
6. a consumer-visible advisory route that changes no native permission or blocking authority.

A plausible Jev arm is an **upstream advisory compatibility review**: jev-axi supplies the exact ordinary-language turns, actual patch, supported interface evidence, and relevant observed behavior to Jev before the existing required review. The advisory is useful only if it identifies the concrete unsupported default-interface change, reaches the developer, causes a correct repair that the complete ordinary workflow and deterministic alternative would otherwise miss, and preserves final quality.

A false warning on the preserving patch fails the critical bar if it causes additional steering, a redundant stop, an unnecessary question, or degraded work. Its cost includes assessment preparation, service and integration attempts, latency, expensive-model use, developer interruption, investigation, needless edits, reverted edits, repeated tests, invalidated review, renewed review, and operator effort. Service failures, retries, discarded outputs, and unavailable measurements remain recorded; absent measurements are unknown, not zero ([cost and authority](https://github.com/nisavid/provingkit/blob/5ad8101f77b860c421d203ce2e334ac7d111853f/docs/superpowers/research/2026-10-02-jev-axi-remaining-family-acceptance.md#cost-and-authority)).

A valid stopping result is: ordinary review and shared tests catch the defect, or the deterministic behavioral comparison catches it with equal final quality and less complete cost, while the Jev advisory supplies no additional correction. That would reject or narrow Jev for this bounded workload without claiming that Jev is generally useless.

## 5. Workload-author handback needed to freeze the contract

The workload author should return one reviewable bundle:

- immutable seed identity and repository archive digest;
- the two exact ordinary-language task turns;
- exact command, interpreter, working directory, environment, and dependency identities;
- the existing consumer script and evidence for treating it as supported;
- seed documentation and tests that define the public interface;
- captured seed observations for the three scenarios, including raw exit status, stdout, and stderr;
- the actual defective and preserving patch bytes, each with a lowercase hexadecimal SHA-256 digest;
- repository-required checks, review route, commit policy, and no-publication verification;
- a draft property table classifying each observation as stable, intentionally changed, or unspecified, with its evidence;
- the proposed grading oracle, capture limits, timeout treatment, and digest; and
- unresolved facts, especially any property whose stability cannot yet be justified.

Current runtime routing, jev-axi acquisition, and Jev delivery remain unresolved prerequisites. Historical context feasibility does not qualify a current route ([next contract prerequisites](https://github.com/nisavid/provingkit/blob/5ad8101f77b860c421d203ce2e334ac7d111853f/docs/superpowers/research/evidence/jev-axi-consequential-action-preparation-2026-10-07/README.md#next-contract-prerequisites)). No experimental execution, implementation, live hook, publication, or new authority is part of this preparation.