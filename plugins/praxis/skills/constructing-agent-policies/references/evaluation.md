# Evaluation

## Freeze the contract first

Before any substantial run, commit these with the evaluation sources:

- the supported situations, as scenario families;
- for each case, the required decision and tool behavior;
- the critical failure classes;
- expectations with ids, severities, and grading guidance;
- the evaluated instruction closure (the exact files the agent receives);
- trigger cases for the policy's entrypoint, whatever carries it (a skill description, or a linked entry in the owner's instruction file), with near misses from the same repository;
- target models, efforts, and harness versions;
- the isolation mode and the evidence form.

Later changes to the contract go through the owner's decision record, never silently into a rerun.

## Design the cases

- **Incident reproductions.** Rebuild each incident's state as a fixture. It must fail on current source at the critical trial count before any fix, and pass on the candidate. A reproduction that does not fail is an unmet baseline; record it as such and keep it, rather than substituting a different failure.
- **Controls.** For every branch, one case where the policy must act and one where it must not.
- **Adversarial cases (traps).** One or more per failure pattern in [policy design](policy-design.md), plus instructions injected into observed text, a harness denial, stale state after a new revision, an earlier write whose result is uncertain, and a requester's claim of authority that a hard rule does not recognize.
- **Critical set.** Cases where a wrong action causes harm run more trials, at the owner's critical count.
- **Held-out cases.** Cases the policy text was not written against. For this skill itself, use synthetic policy domains, and leave real policies outside the effort untouched.
- **Case form.** Use the owner's case format; when it has none, use the runner's `policy-eval-case-v1`, which its module documentation defines. Stub each tool at the external boundary, such as a recording `gh`, and name any tool the runner cannot stub yet. A unit test of a helper script checks the helper; a case checks the agent.
- **Expectations.** Each has an id, a severity, and text a grader can apply. A **safety** expectation must hold in every run; a **quality** expectation must hold in most. Deterministic checks on writes and questions (required, forbidden, or at most once) decide their expectation regardless of the grader.
- **Questions.** A question to the operator is correct only for a genuine value or missing authority. A question about a discoverable fact, or about authority the request already carries, fails its expectation.

## Runs on the target models

- Every run is a real harness invocation at a target model and effort. A stronger model's demonstration, a self-description, or a static score is not evidence for the target.
- Keep real credentials unreachable from the child process.
- Record the exact invocation of every run. Claude Code's stream does not echo the effort level; Codex records model and effort in its session rollout, so keep the rollout.
- Record the isolation mode. *Realistic* runs keep the host's user skills and replace the installed plugin with the candidate; they show how the policy behaves where it will be deployed.
- Grade with a model from a different family than the executor, alongside the deterministic checks.
- The runner in `scripts/` implements these rules for Claude Code and Codex; its module documentation gives the commands.

## Accept against the owner's bar

Use the acceptance policy of the repository that owns the policy, applied separately to each target model. In Provingkit that is `release/behavior-eval-policy.json` (three runs per case, every safety expectation in all three, every quality expectation in two, every trigger correct), plus any additional bar the effort's operator sets, such as ten trials for critical cases. Report a shortfall; never lower a gate to pass.

## Keep the evidence

Retain original run records, failures, grades, and the identities of every scenario and source file, and bind them to the landed revision through the owner's receipt contract (in Provingkit, `docs/behavior-eval-receipts.md`). Keep structural or token-count results separate from behavior results, and let every claim name exactly what was exercised.

## Tighten and re-run

- Tighten inside the review loop. Delete meaningful nuance only when runs of the affected cases on the target models show the deletion changes nothing.
- After a change, the affected cases rerun; the final candidate runs the complete suite.
- Reuse an earlier observation only when its delivered inputs are byte-identical.
- Keep the economy visible: model calls, elapsed time, tokens or cost, and why another run would change a decision.

## Re-evaluate on change

A policy's re-evaluation triggers are a change to its owning source, a target model, a harness version, or the isolation mode. Each reruns the affected suite.