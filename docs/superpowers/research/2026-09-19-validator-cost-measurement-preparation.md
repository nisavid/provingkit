# Prepare attribution of remaining validator costs

This specification defines a smaller measurement that separates fixture preparation, validator phases, Git subprocess work, filesystem acquisition, and unassigned time. It supports selecting the next investigation for [Which remaining validator costs justify the next optimization?](https://github.com/nisavid/provingkit/issues/156). It does not qualify a procedure, establish a performance result, or authorize execution.

The subject remains commit [`89d895269db5652aafa9ff9a642114585e7bb709`](https://github.com/nisavid/provingkit/tree/89d895269db5652aafa9ff9a642114585e7bb709). The starting proposal is the [published remaining-cost report](https://github.com/nisavid/provingkit/blob/51a113be0df38509316d8ddf11ce83bb7f989e74/docs/superpowers/research/2026-09-19-remaining-validator-costs.md). I inspected source and completed run artifacts only; I executed no subject code, tests, or profiles.

## Workload

Use seven sequential workload entries:

| Order | Kind | Work |
|---|---|---|
| 1 | Ordinary | Positive validator CLI |
| 2 | Ordinary | Complete rejection method |
| 3 | Ordinary | Complete accepted encoded-authority method |
| 4 | Diagnostic | Complete rejection method, with fixture observations |
| 5 | Diagnostic | Complete accepted encoded-authority method, with fixture observations |
| 6 | Diagnostic | Complete positive validator, with phase observations and CPU profile |
| 7 | Ordinary | Positive validator CLI |

The existing commands are:

```sh
python scripts/validate_provingkit.py .
```

```sh
python -m unittest tests.test_validate_provingkit.ProvingkitRepositoryContractTests.test_unallowlisted_legacy_repository_identity_is_rejected
```

```sh
python -m unittest tests.test_validate_provingkit.ProvingkitRepositoryContractTests.test_encoded_scheme_does_not_decode_percent_authority
```

Run each from the frozen disposable subject checkout. The future controller must invoke the ordinary commands unchanged, without injected instrumentation.

The rejection method contains one validator invocation and no subtests. The accepted method contains two validator invocations and two named subtests, `json-unicode` and `html-entity`. Preserve both complete methods, all original assertions, fixture inputs, and subtest boundaries. Diagnostic method runs must retain the original helper’s subprocess arguments:

```python
[sys.executable, str(VALIDATOR), str(repository)]
```

These behaviors are defined by the [fixture helpers](https://github.com/nisavid/provingkit/blob/89d895269db5652aafa9ff9a642114585e7bb709/tests/test_validate_provingkit.py#L25-L192), [rejection method](https://github.com/nisavid/provingkit/blob/89d895269db5652aafa9ff9a642114585e7bb709/tests/test_validate_provingkit.py#L1733-L1738), and [accepted method](https://github.com/nisavid/provingkit/blob/89d895269db5652aafa9ff9a642114585e7bb709/tests/test_validate_provingkit.py#L2460-L2481).

This reduces the initial ten workload entries and thirteen validator executions to seven entries and nine validator executions. The completed [main run](https://github.com/nisavid/provingkit/actions/runs/35409128973) already records these two methods succeeding in approximately 19.075 and 41.177 seconds. Repeating each ordinary method three times would add cost without supplying the missing fixture attribution. Two positive CLI samples bracket the measurement to expose gross drift; they do not establish variance, cold-cache behavior, or repeatability.

No executable command is specified for the proposed controller: it has not been built. Its reviewed interface must eventually identify the source commit, driver identity, output directory, fixed workload, and enforced resource profile.

## Observation boundaries

Use monotonic wall time, current-process user/system CPU, and waited-child user/system CPU as separate fields. Every event needs an identifier, parent identifier, start/end timestamps, outcome, and explicit completeness state.

### Ordinary execution

The controller records command launch through process completion, return code, stdout/stderr, and resource observations. It makes no internal attribution claims.

Record controller/setup/collection time outside each command interval. No fixture wrappers, profiler injection, or changed validator argument list may enter an ordinary sample.

### Diagnostic fixture execution

A separate diagnostic worker imports the unchanged test module and runs each selected complete method through `unittest`, using a result recorder that retains method and subtest outcomes.

Install scoped delegating wrappers; call the original function exactly once and preserve its return value or exception:

| Observation | Placement and meaning |
|---|---|
| Complete method | `unittest` start/stop boundaries, including assertions and fixture teardown |
| Fixture | `assert_identity_fixture` entry/exit |
| Clone preparation | `clone_with_history` entry/exit, inclusive |
| Clone subprocess | Original `git clone --quiet --shared --no-hardlinks` call |
| Retained-ref restoration | Three source `rev-parse` calls and three destination `update-ref` calls, individually recorded |
| Contract overlay | `overlay_current_final_main_contract` entry/exit, including its copies, removals, and directory operations |
| Validator subprocess | `validate` entry/exit and the unchanged delegated subprocess call |
| Temporary-directory cleanup | Owned `TemporaryDirectory.cleanup` calls, including failures |
| Unassigned fixture work | Fixture interval minus the union of its directly attributed intervals |
| Unassigned method work | Method interval minus the union of fixture intervals |

The [`clone_with_history` implementation](https://github.com/nisavid/provingkit/blob/89d895269db5652aafa9ff9a642114585e7bb709/tests/test_validate_provingkit.py#L33-L74) combines clone, retained refs, and overlay. Its inclusive time must never be presented as clone-only time.

Associate cleanup with the owned fixture directory. Overlay removals belong to overlay, not final cleanup. Measure teardown before declaring the fixture complete: the original helper performs its result assertions after leaving the temporary-directory context.

Use scoped subprocess observations to distinguish clone and retained-ref calls. Do not wrap or replace validator subprocess contents in these diagnostic method runs. Python phase attribution comes from the separately labeled positive diagnostic.

### Diagnostic validator execution

A diagnostic worker loads the original validator module from the frozen checkout, installs wrappers in that module’s global namespace, and calls its original `main` with the same repository argument. Record this as a diagnostic invocation of the source implementation, not as the ordinary CLI.

Record module loading separately. Wrap all eight ordered phases from [`main`](https://github.com/nisavid/provingkit/blob/89d895269db5652aafa9ff9a642114585e7bb709/scripts/validate_provingkit.py#L2407-L2432):

1. Definition.
2. Excluded source.
3. Marketplace.
4. Cutover provenance.
5. Historical qualification boundary.
6. Historical identities.
7. Release boundary.
8. History.

Capture wall time and self CPU for each phase, including exceptional exits. Keep unassigned `main` time and worker startup/reporting time separate.

Within those phases:

- Record `_identity_scan_content` and `_normalize_identity_scan_file` separately by repository-relative path. The latter includes YAML/frontmatter extraction and content normalization.
- Use `cProfile.Profile(timer=time.process_time)` around the original `main` invocation. Retain raw statistics and function-level exclusive and cumulative CPU columns.
- Observe both `_run_git` and `_require_git_bytes`, because the byte-returning helper launches subprocesses independently. Avoid counting `_require_git_output` as another launch. Record arguments, command family, wall duration, self CPU, waited-child CPU delta, return code, and timeout/error state.
- Observe repository `Path.read_bytes` and `Path.read_text` operations with phase, path, call count, returned-byte or character count, wall time, and self CPU. Keep text-character counts distinct from byte counts.
- Observe directory enumeration during iterator advancement, not only when the `rglob` or `iterdir` iterator is created. Time metadata operations separately where observed; leave sorting and unobserved filesystem work in the containing phase’s remainder.

The relevant source boundaries are [normalization](https://github.com/nisavid/provingkit/blob/89d895269db5652aafa9ff9a642114585e7bb709/scripts/validate_provingkit.py#L704-L841), [identity enumeration and reads](https://github.com/nisavid/provingkit/blob/89d895269db5652aafa9ff9a642114585e7bb709/scripts/validate_provingkit.py#L1611-L1694), [release-boundary reads](https://github.com/nisavid/provingkit/blob/89d895269db5652aafa9ff9a642114585e7bb709/scripts/validate_provingkit.py#L1827-L1871), and [Git acquisition](https://github.com/nisavid/provingkit/blob/89d895269db5652aafa9ff9a642114585e7bb709/scripts/validate_provingkit.py#L1883-L1938).

## Accounting limits

Maintain a hierarchy of intervals and derive exclusive wall time by subtracting the union of child intervals. Never add nested cumulative durations. Reject inconsistent interval trees rather than silently clamping substantial negative remainders.

The profile measures CPU consumed by the profiled Python process. It does not charge Git child CPU to the Python function that waits for Git. Sequential `RUSAGE_CHILDREN` deltas around synchronous subprocess calls can attribute waited-child CPU when no other children are reaped in that interval; synthetic checks must establish that condition.

Keep these distinctions explicit:

- Git-wrapper wall time includes launch, Git work, communication, and waiting. It is not launch overhead.
- Read-wrapper wall time includes Python conversion and cached reads. It is not physical disk service time.
- A parent’s waited-child CPU can already include descendants accounted through waits. Do not add it again to descendant totals.
- Per-process peak RSS is not concurrent aggregate memory and must not be summed.
- Instrumentation overhead remains inside diagnostic observations. It cannot be removed by subtracting a single guessed constant.
- The positive diagnostic covers phases that identity rejection never reaches. It does not establish identical phase proportions for every fixture.

Compare diagnostic elapsed time with ordinary observations only as an overhead sanity check. Keep both visible; derive no corrected baseline or suite-wide savings.

## Frozen inputs and restoration

Before later execution:

- Freeze driver bytes and digest, source commit, tracked-file content/modes, index state, all refs and symbolic refs, retained-ref targets, shallow state, Git configuration relevant to execution, and object-store/alternate relationships.
- Require complete local history and the three retained remote refs used by the fixture helper. Resolve setup before starting the workload; do not fetch or repair midway.
- Put controller code, evidence, dependencies, and temporary directories outside the subject checkout. The validator scans untracked files too; tracked-file equality alone is insufficient.
- Use Python 3.13.15 and the completed run’s dependency inventory for the closest available comparison. The workflow pins `idna==3.18`, `jsonschema==4.26.0`, and `PyYAML==6.0.3`; the run also records the transitive versions. Record pytest absence, locale, Git version, platform, CPU observations, and cache conditions. The [workflow](https://github.com/nisavid/provingkit/blob/89d895269db5652aafa9ff9a642114585e7bb709/.github/workflows/provingkit-source.yml#L29-L46) selects Python 3.13, whereas the completed artifact identifies 3.13.15.
- Set the existing workflow’s `PYTHONDONTWRITEBYTECODE=1` consistently. Give every worker owned temporary storage without changing the parent environment.
- Restrict in-process patches to diagnostic workers; restore descriptors, functions, profiler state, cwd, environment changes, and `sys.argv` in `finally` paths.

Compare the full source manifest, index, refs, configuration, and alternate relationships after each workload entry and at finalization. On unexpected drift, stop and preserve evidence. Do not restore source or refs by overwriting the discrepancy. Remove only owned fixture directories and owned disposable execution state after process cleanup.

## Output contract

The proposed evidence directory contains:

- `manifest.json`: source and driver identities, workload, expected outcomes, resource contract, supported environment, and schema version.
- `environment.json`: observed interpreter, distributions, Git/platform information, locale, affinity, quota observations, and declared environment changes.
- `source-before.json` and `source-after.json`: frozen inputs and comparison.
- `executions.jsonl`: ordered workload records with argv, kind, times, return codes, expected/observed outcomes, logs, completeness, and resource observations.
- `events.jsonl`: hierarchical fixture, phase, Git, read, enumeration, and cleanup events.
- Raw `cProfile` statistics and a derived table retaining exclusive/cumulative distinctions.
- `cleanup.json`: owned process groups/cgroup, escalation actions, surviving members, temporary-directory outcomes, and deadline state.
- `result.json`: `complete`, `successful`, stop reason, missing observations, source comparison, limits reached, and artifact digests.

Require exactly seven completed workload entries, two successful selected methods per diagnostic/ordinary pair, all expected accepted subtests, no skips, no duplicate/missing events, and complete cleanup. The rejection validator’s nonzero return is expected; its complete test method must still succeed. Preserve failed and incomplete evidence, with explicit missing fields rather than fabricated zeroes.

## Resource contract and feasibility

The proposed execution budget is one machine, one subject workload at a time, two CPUs, 4 GiB aggregate memory, 1 GiB retained output, and a 900-second overall envelope. These limits remain a proposal until the concrete run is allocated. Reserve the final 30 seconds for termination, cleanup, and final reporting; stop admitting subject work at 870 seconds.

The current [`run_provingkit_tests.py`](https://github.com/nisavid/provingkit/blob/89d895269db5652aafa9ff9a642114585e7bb709/scripts/run_provingkit_tests.py) observes CPU capacity and runs two workers. It does not enforce the proposed CPU, memory, or output ceilings. There is no separate `scripts/provingkit_ci_resources.py` at this revision.

The future driver must qualify actual enforcement before subject execution:

- A delegated cgroup or equivalent must cover the run’s processes and descendants, with CPU and aggregate memory limits. Record swap policy and controller overhead explicitly.
- Process groups support cooperative cleanup; an owned cgroup adds descendant enumeration and termination even after leaders exit. Synthetic checks must cover orphaned descendants.
- Capped log writers alone do not enforce a total output limit. Use a quota-backed output area or demonstrate complete accounting and bounded writing across every producer. Preserve capacity for failure metadata.
- Temporary clones need a separately explicit storage bound; the output allowance must not silently stand in for scratch-space control.
- Missing control surfaces, unavailable observations, source drift, unexpected results, output exhaustion, OOM, timeout, or failed cleanup stop the run without automatic retry.

A hard host kill can prevent cleanup and reporting. Missing completion evidence never establishes success.

The unresolved enforcement details are implementation and environment-qualification work. Their availability has not been inspected here.

## Implementation and qualification sequence

1. **Freeze the contract.** Finalize workload order, event schema, accounting hierarchy, resource coverage, scratch bound, and expected result records.
2. **Build the disposable controller.** Implement ordinary subprocess execution and evidence/cleanup behavior first. Add diagnostic adapters without changing production source.
3. **Qualify with synthetic subjects only.** Exercise success, expected rejection, exceptions, skipped/failed subtests, malformed/missing records, timeout, cancellation, output exhaustion, child CPU attribution, orphaned descendants, and cleanup failure. Verify exact ordinary argv and preserved delegated return values/exceptions.
4. **Qualify attribution.** Use synthetic nested phases and repeated reads to check exclusive accounting; use a CPU-consuming child to demonstrate that parent profiling and child CPU differ. Exercise lazy enumeration, fixture cleanup on assertion failure, and restoration after wrapper exceptions.
5. **Review the frozen driver and procedure together.** Review measurement correctness, unchanged assertions, attribution limitations, restoration, and resource hygiene against the same revision. Any relevant change invalidates affected checks.
6. **Return the executable proposal.** Supply the actual command, driver digest, synthetic evidence, enforced limits, and remaining environmental gaps for the execution decision. Do not run the production subject as part of this preparation.

## Procedure capture and consumer

Use `capturing-agent-procedures` to extend the existing maintained source, [`docs/agents/provingkit-test-execution.md`](https://github.com/nisavid/provingkit/blob/89d895269db5652aafa9ff9a642114585e7bb709/docs/agents/provingkit-test-execution.md), with a focused validator-cost diagnosis route when its driver and method are qualified. Keep this research specification as rationale rather than presenting it as settled operating guidance.

The future optimization consumer must load that reviewed procedure, record its revision and driver identity, verify complete measurement evidence, and retain unresolved attribution before choosing an optimization. Discovery checks should distinguish cost-diagnosis requests from ordinary source acceptance and schedule-balancing work.

No stakeholder policy decision is required before bounded driver implementation. The next concrete implementation question is which available control surface can enforce the stated descendant, CPU, memory, output, and scratch limits; resolve that before proposing subject execution.
