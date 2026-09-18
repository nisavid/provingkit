# Measure complete-method CI schedules

The scheduling experiment measures the unchanged Provingkit test suite in three
separate hosted phases: serial, two processes on one runner, and four isolated
runner jobs. It produces method timings and complete execution records for the
[CI scheduling evidence question](https://github.com/nisavid/provingkit/issues/121).

The experiment pins candidate `ad31344cdcb9891438cf1e92c27c776945bee6ab`.
The measurement scripts come from a separately reviewed harness revision.
The production workflow and required **Provingkit source boundary** check remain
the acceptance path. These experimental jobs measure only
`tests.test_validate_provingkit`; they do not qualify the other standalone,
prepared, member, artifact, projection, exclusion, or derived-lock obligations.

## Prepare and review

Run these checks on the harness revision:

```sh
python -B -m unittest tests.test_measure_provingkit_suite tests.test_ci_measurement_phase
actionlint .github/workflows/ci-scheduling-experiment.yml
git diff --check
```

Review the runner, phase controls, workflow, and this procedure together. Keep
the production validator and test module unchanged. Verify an actual candidate
discovery and a bounded real-method smoke run separately from the constructed
fixtures. Fixture checks exercise failures, missing results, intentional skips,
and subtests; they are not a full candidate-suite result.

Record the reviewed harness commit, candidate commit, full ref inventory,
required retained refs, suite discovery digest, dependency versions, Python
version, runner image, affinity, visible CPU quotas, and pytest presence.
Use the repository's ordinary checkpoint and publication procedure. The
preparation branch `ivan/ci-scheduling-measurements` does not launch this workflow.

## Launch one phase at a time

The preview orchestrator owns the shared CI window. Before each launch, fully
paginate queued and in-progress repository runs and obtain that owner's window
clearance for the concrete publication plan. Reserved rollout work takes
priority. Publish only the reviewed harness commit to the phase's dedicated
branch:

| Phase branch | Execution | Prerequisite |
| --- | --- | --- |
| `ivan/ci-measure-serial` | Every discovered method, serially | Reviewed harness and cleared window |
| `ivan/ci-measure-injob2` | Two balanced whole-method processes | Successful serial run and observed capacity of at least two CPUs |
| `ivan/ci-measure-shards4` | Four balanced whole-method jobs, then aggregate | Successful serial run and cleared four-job window |

Use the same harness commit for every phase. A changed harness requires a new
serial baseline. Do not overlap phases, add a four-process in-job trial, change
runner tiers, or rerun a trial without resolving the new experiment scope with
the orchestrator. The baseline selector rejects duplicate runs and reruns; a
failed baseline needs a separately reviewed recovery plan.

The serial phase fetches complete history, records acquisition, and creates a
Git bundle containing all refs and HEAD. Every measured phase, including serial,
restores a fresh owned clone through the same bundle acquisition path. Restoration
verifies the bundle SHA-256, HEAD, tree, refs, required retained refs, reachable
object inventory, annotated tags, and source hashes. Later arms also require the
serial clone's complete source identity, including material Git checkout settings
and bundle digest. They do not fetch the evolving origin namespace. System and
global Git configuration are disabled; locale and timezone are fixed and recorded.
CPython 3.13 runs in an isolated virtual
environment with `idna==3.18`, `jsonschema==4.26.0`, and `PyYAML==6.0.3`.
Serial records a complete installed-distribution freeze, including transitive
dependencies and pip. Later phases install from that file and compare the full
normalized distribution/version inventory with serial.
The recorded presence or absence of pytest must match across phases.

The planner uses descending measured method duration, assigning each method to
the least-loaded worker and retaining discovery order within each worker.
Methods are indivisible, including their subtests and assertions. Every worker
uses the candidate's own module imports. Mutable test fixtures remain separate;
workers share only immutable candidate source. Results must cover the discovered
methods exactly, with no unknown, missing, or duplicate IDs. The final aggregate
requires every expected shard and a compatible source, plan, and environment.
Each method must retain its serial outcome, subtest counts, and skip reasons.
Ordinary worker failures retain their result and fail the phase. Canceled,
timed-out, skipped, or missing jobs cannot produce a successful phase.
The in-job controller cleans every owned worker process group, including
descendants whose interpreter leader has already exited.

## Interpret and preserve results

Download artifacts before their 30-day retention expires. Preserve their exact
bytes and hashes with the report, alongside workflow/job metadata and logs.
Keep successful execution, failed attempts, and constructed fixture conditions
distinct. The serial bundle is a reproducible experimental input, not permission
to replace a checkout or publish a source change.

Report these measurements separately:

- Suite/controller elapsed time and workflow critical-path elapsed time.
- Sum of method durations and measured process CPU, including waited-for child
  processes where the runtime reports it.
- Sum of occupied runner time, including setup and aggregation; distinguish
  this from billing, quota, or cost estimates.
- Actual CPU capacity and runner variation, fixture isolation, skipped methods
  and reasons, subtest results, and failures or incomplete execution.

A longest-first schedule's predicted maximum is an estimate until executed.
A single trial per arm does not establish variance or a stable speedup. Compare
only compatible inputs and report environmental differences. The experiment
contains no scanner fast path, so its observations concern scheduling alone.
The frozen bundle does not replace final production validation against current
source, refs, and every owning acceptance obligation.

Return evidence to the orchestrator for acceptance before resolving the issue,
adding its unique decision pointer to the Wayfinder map, and closing the issue
last. The worker-layout decision consumes the accepted report. Any eventual
production workflow change requires its own implementation and acceptance
evidence, including the required check and the other owning checks.

This procedure is local to the pinned experiment. Its workflow and phase scripts
are the direct consumers. Hosted execution establishes its remaining operational
evidence; promotion into general agent instructions requires a separate review.
