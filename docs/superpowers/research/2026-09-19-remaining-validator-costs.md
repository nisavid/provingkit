# Remaining validator costs and the next measurement

I would separate fixture preparation from complete validator execution before choosing another optimization for [the remaining-cost investigation](https://github.com/nisavid/provingkit/issues/156). Existing evidence puts that combined test phase ahead of other source-job work, but it does not establish a current ranking among identity normalization, Git acquisition, and fixture preparation. This investigation used source and completed evidence only; I ran no validator, test, or profile.

The source is [`89d895269db5652aafa9ff9a642114585e7bb709`](https://github.com/nisavid/provingkit/tree/89d895269db5652aafa9ff9a642114585e7bb709). The [earlier research](https://github.com/nisavid/provingkit/blob/ce5dc47d034c4b8df462b9536e70ffe57b1fb6b8/docs/superpowers/research/2026-09-18-ci-performance-architecture.md) supplies hypotheses; its measurements predate the landed inert-token decoding guard and cannot rank present costs.

## What the completed run establishes

The [source-boundary job](https://github.com/nisavid/provingkit/actions/runs/35409128973/job/105804985556) occupied 1,749 seconds. Its complete-method command took 1,686.825 seconds: 95 methods completed with 94 successes, one skip for unavailable pytest, and 146 successful subtests. Approximately 62.2 seconds remained for **all other source-job work**, including independent checks and infrastructure overhead. That remainder is not an overhead-only measurement.

Across the [nine jobs](https://github.com/nisavid/provingkit/actions/runs/35409128973), occupied runner time totaled 2,301 seconds. This is summed job duration, not billing or summed worker CPU. The source job finished last.

The two longest methods took 364.569 and 349.577 seconds, covering 19 and 17 successful subtests. Their URL-oriented names do not identify the expensive function: each fixture invokes the complete validator. The runner measures [whole methods and aggregate worker resources](https://github.com/nisavid/provingkit/blob/89d895269db5652aafa9ff9a642114585e7bb709/scripts/run_provingkit_tests.py#L127-L151), with [CPU including waited-for children](https://github.com/nisavid/provingkit/blob/89d895269db5652aafa9ff9a642114585e7bb709/scripts/run_provingkit_tests.py#L270-L292), rather than per-validator phases.

The supported priority is therefore cost attribution within the complete-method phase. Its records combine fixture preparation and validator execution; they do not establish which contributes more. No narrower cost ranking is yet measured.

## Opportunities and uncertainties

**Identity normalization and parsing remain plausible substantial costs.** The [landed guard](https://github.com/nisavid/provingkit/blob/89d895269db5652aafa9ff9a642114585e7bb709/scripts/validate_provingkit.py#L770-L834) skips token decoding when the token contains no escape introducer. JSON extraction, YAML/frontmatter parsing, URL recognition, whole-content normalization, and repository enumeration remain. A fresh profile must separate Python CPU from filesystem acquisition; the guard’s presence alone establishes neither dominance nor further savings.

**Grouped Git acquisition remains a concrete candidate, with unknown payoff.** The [two history loops](https://github.com/nisavid/provingkit/blob/89d895269db5652aafa9ff9a642114585e7bb709/scripts/validate_provingkit.py#L2146-L2258) acquire parents, messages, and raw tree deltas separately. Measure launch counts, combined acquisition wall time, and Git child CPU. Wrapper duration includes useful Git work and process overhead; it is not a measurement of launch overhead alone. The [CLI ordering](https://github.com/nisavid/provingkit/blob/89d895269db5652aafa9ff9a642114585e7bb709/scripts/validate_provingkit.py#L2407-L2432) also matters: identity rejection happens before history validation, limiting which executions could benefit.

**Fixture changes and shared file acquisition lack current justification.** The [fixture helpers](https://github.com/nisavid/provingkit/blob/89d895269db5652aafa9ff9a642114585e7bb709/tests/test_validate_provingkit.py#L25-L74) clone history, restore retained refs, and overlay contract files; each [identity fixture](https://github.com/nisavid/provingkit/blob/89d895269db5652aafa9ff9a642114585e7bb709/tests/test_validate_provingkit.py#L167-L192) additionally writes its input and cleans up. Existing method records combine these costs with validation. Repeated reads or helper calls demonstrate repetition, not material expense.

Making each invocation cheaper could reduce both complete-suite elapsed time and occupied runner time. Actual elapsed savings depend on which worker’s methods benefit. Schedule balancing remains [a separate decision](https://github.com/nisavid/provingkit/issues/155).

## Smallest proposed profiling increment

I propose a disposable measurement driver, reviewed and frozen before execution. It would leave production source and every original CLI test unchanged. This is a command proposal for that driver, not an existing repository command:

```sh
python "$HARNESS/profile_validator_costs.py" \
  --source . \
  --commit 89d895269db5652aafa9ff9a642114585e7bb709 \
  --output "$EVIDENCE" \
  --repetitions 3 \
  --deadline-seconds 900
```

Use a disposable checkout with complete history and required retained refs, Python 3.13.15, and the run’s pinned dependencies. Keep output outside the checkout. Freeze the driver digest, tracked-file hashes, retained refs, and dependency inventory.

Its fixed workload would be:

1. Three ordinary executions of `python scripts/validate_provingkit.py .`.
2. Three repetitions of the unchanged complete methods `test_unallowlisted_legacy_repository_identity_is_rejected` and `test_encoded_scheme_does_not_decode_percent_authority` in `tests.test_validate_provingkit.ProvingkitRepositoryContractTests`, retaining every assertion and subtest.
3. One separately labeled diagnostic execution of the complete positive validator, profiling Python CPU with `cProfile` using `time.process_time`, and recording Git-wrapper wall time and waited-child CPU.

The driver would time original fixture helpers through delegating wrappers, preserving their arguments and original subprocess command. Record clone preparation, validator subprocess, total method duration, and unattributed remainder separately. Diagnostic records should include phase CPU, per-file normalization attribution, Git command-family counts and durations, filesystem read attribution, exit statuses, and raw profiles. Nested cumulative entries must not be added.

Bound execution to one machine, one subject execution at a time, a two-CPU ceiling, 4 GiB memory, 1 GiB output, and 900 seconds overall. Stop on source/ref drift, unexpected outcomes or skips, incomplete records, resource limits, or failed descendant cleanup; retain partial evidence and do not retry automatically.

This sample distinguishes common validator costs and fixture preparation without claiming whole-suite savings or acceptance equivalence. If it leaves the ranking unclear, report the unresolved distinction before proposing another measurement. Any acceptance-affecting optimization needs its later applicable independent review.

The next step is to prepare and review the bounded driver and its procedure. The driver does not exist yet, and this note allocates no execution. Return the reviewed driver, exact command, and enforced resource limits for an execution decision. Its maintained procedure should extend [`docs/agents/provingkit-test-execution.md`](https://github.com/nisavid/provingkit/blob/89d895269db5652aafa9ff9a642114585e7bb709/docs/agents/provingkit-test-execution.md), using `capturing-agent-procedures` to bind the qualified method to its next optimization consumer.
