# Evaluation

## Freeze the contract first

Before any substantial run, commit these with the evaluation sources:

- the supported situations, as scenario families;
- for each case, the required decision and tool behavior;
- the critical failure classes;
- expectations with ids, severities, and grading guidance;
- the evaluated instruction closure (the exact files the agent receives);
- trigger expectations for the owning skills;
- target models, efforts, and harness versions;
- the isolation mode and the evidence form.

Later changes to the contract go through the owner's decision record, never silently into a rerun.

## Design the cases

- **Incident reproductions.** Rebuild each incident's state as a fixture. It must fail on current source at the critical trial count before any fix, and pass on the candidate. A reproduction that does not fail is an unmet baseline; record it as such and keep it, rather than substituting a different failure.
- **Controls.** For every branch, one case where the policy must act and one where it must not.
- **Adversarial cases.** One or more per failure pattern in [policy design](policy-design.md), plus instructions injected into observed text, a harness denial, stale state after a new revision, and an earlier write whose result is uncertain.
- **Critical set.** Cases where a wrong action causes harm run more trials, at the owner's critical count.
- **Held-out cases.** Cases the policy text was not written against. For this skill itself, use synthetic policy domains, and leave real policies outside the effort untouched.
- **Expectations.** Each has an id, a severity, and text a grader can apply. A **safety** expectation must hold in every run; a **quality** expectation must hold in most. Deterministic tool-call checks (required, forbidden, or at-most-once writes) decide their expectation regardless of the grader.
- **Questions.** A question to the operator is correct only for a genuine value or missing authority. A question about a discoverable fact, or about authority the request already carries, fails its expectation.

## Run on the target models

- Use real harness invocations at the target models and efforts. A stronger model's demonstration, a self-description, or a static score is not evidence for the target.
- Stub tools at the external boundary, such as a recording `gh`, and keep real credentials unreachable from the child process.
- Record the exact invocation of every run. Claude Code's stream does not echo the effort level; Codex records model and effort in its session rollout, so keep the rollout.
- Record the isolation mode. *Realistic* runs keep the host's user skills and replace the installed plugin with the candidate; they show how the policy behaves where it will be deployed.
- Grade with a model from a different family than the executor, alongside the deterministic checks.
- The runner in `scripts/` implements these rules for Claude Code and Codex; its module documentation gives the case format and commands.

## Accept against the owner's bar

Use the acceptance policy of the repository that owns the policy, applied separately to each target model. In Provingkit that is `release/behavior-eval-policy.json` (three runs per case, every safety expectation in all three, every quality expectation in two, every trigger correct), plus any additional bar the effort's operator sets, such as ten trials for critical cases. Report a shortfall; never lower a gate to pass.

## Keep the evidence

Retain original run records, failures, grades, and the identities of every scenario and source file, and bind them to the landed revision through the owner's receipt contract (in Provingkit, `docs/behavior-eval-receipts.md`). Keep structural or token-count results separate from behavior results, and let every claim name exactly what was exercised.

## Tighten and re-run

- Tighten inside the review loop. Before deleting meaningful nuance, run the affected cases on the target models and delete only what changes nothing.
- After a change, rerun the affected cases; run the complete suite on the final candidate.
- Reuse an earlier observation only when its delivered inputs are byte-identical.
- Keep the economy visible: model calls, elapsed time, tokens or cost, and why another run would change a decision.

## Re-evaluate on change

Rerun the affected suite when the policy's owning source, a target model, a harness version, or the isolation mode changes. Record these triggers where the owner keeps them.