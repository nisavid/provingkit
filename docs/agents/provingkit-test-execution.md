# Run complete Provingkit contract methods

Use this procedure to run, change, or diagnose the complete-method test
schedule: `scripts/run_provingkit_tests.py` runs every test method of
`tests.test_validate_provingkit` (the suite), each one whole, in one or two
worker processes. The production consumer is the **Provingkit source boundary**
job in `.github/workflows/provingkit-source.yml`, and the runner's regression
suite is `tests/test_run_provingkit_tests.py`. Other member checks and the
standalone source validator keep their own routes.

To change or qualify the schedule itself, also follow
[Change and qualify the schedule](#change-and-qualify-the-schedule), which adds
a coordination step for that operation.

## Run the candidate

1. Use a Linux checkout with complete Git history and the retained refs the
   suite reads, under `refs/remotes/origin/retained/` (the published
   repository's `retained/` branches). Keep its tracked files and its Git
   object store unchanged for the run; the suite's per-test `--shared` clones
   borrow that object store. For a hosted comparison, use the Python version
   the workflow sets up and the dependencies in `requirements.txt`. Record the
   candidate commit and whether local validation differs from that
   environment, including pytest presence.
2. Read this procedure from that candidate revision. Run the command with a new
   output directory outside the candidate; the runner rejects one inside it or
   one that already exists:

   ```sh
   python scripts/run_provingkit_tests.py . --output-dir /tmp/provingkit-tests
   ```

   The default `--workers 2` requires an observed capacity of at least two CPUs,
   bounded by affinity and every visible ancestor cgroup quota. Missing
   observations or insufficient capacity fail before test workers start, and
   `result.json` records the capacity observed.
   For local functional validation, explicitly select serial execution when
   capacity is unknown or insufficient for two workers:

   ```sh
   python scripts/run_provingkit_tests.py . --workers 1 --output-dir /tmp/provingkit-tests-serial
   ```

   For the limits of serial execution, including that it does not extend the
   deadline, see
   [How the schedule runs the suite](#how-the-schedule-runs-the-suite).
3. Require exit status zero, `result.json` with `successful: true`, the selected
   `worker_count` in `plan.json` and `result.json`, a `worker-N.json` report and
   a `worker-N.log` for each selected worker (`N` is 0 or 1), and successful
   `discovery-cleanup.json` and `cleanup.json` records. Every discovered method
   must appear exactly once with a completed outcome. Inspect method and subtest
   skips and their reasons; a skipped optional dependency remains a missing
   runtime observation.

## What a passing run establishes

Before claiming source acceptance, complete the standalone validator,
projection, prepared entrypoint, exclusion, member, artifact, and derived-lock
checks in the source workflow. The workflow file is the current list of those
checks.

A successful serial run establishes complete local functional execution only
when coverage, outcomes, source stability, and cleanup all pass. It does not
qualify the two-worker schedule or parallel fixture isolation, establish hosted
timing, or replace required production status checks. An unknown CPU capacity
remains unknown after a successful serial run.

## How the schedule runs the suite

The controller discovers the current module in a separate process. Each worker
rediscovers the full module before selecting its assigned whole methods. Every
assertion and subtest stays inside its method. Mutable fixtures use separate
worker temporary directories and the existing per-test temporary clones; only
the candidate source and its Git objects are shared. New tests must preserve
that isolation. Review any new shared module/class fixture before using this
schedule.

Serial execution retains CPU observations, errors, and unknown capacity;
it makes no minimum-capacity claim. The host scheduler and quotas govern
execution. The fixed budget is one controller and the selected one or two
complete-method test workers, with their ordinary descendants. Serial mode
does not impose a one-CPU utilization cap or extend the deadline.

`scripts/provingkit_test_timings.json` supplies advisory duration estimates.
With two workers, longest-first assignment balances their estimated loads while
retaining discovery order inside each worker. Serial execution puts every
method in one worker in discovery order. New methods receive the longest current
estimate; obsolete hint names are ignored. `plan.json` records each worker's
estimate as `estimated_seconds`. Hints never define coverage or
acceptance. The initial estimates come from the accepted
[serial measurement](https://github.com/nisavid/provingkit/actions/runs/35374474769).
Updating estimates requires complete successful current-run records and review;
there is no dependency on a frozen source, prior hosted run, or experiment branch.

## Diagnose and retain execution

Keep the complete output directory for failed as well as successful runs. Once
the runner has created it, CI uploads it as the `provingkit-test-execution`
artifact whether or not the job passes, and retains it for 30 days.

Start with `result.json`, unless the runner rejected the output directory: it
then writes nothing there, so any `result.json` there is from an earlier run.
When the controller fails the run, `error` gives the cause, which the runner
also prints to standard error. When `successful` is false and there is no
`error`, a worker reported an unsuccessful run; use the method records and
worker logs to locate the test or fixture failure. A missing `result.json` means the controller
never reported: read standard error. The directory also holds:

- `source-before.json` and `source-after.json`: tracked-source snapshots, with
  the commit, the retained refs found, and whether the checkout is shallow.
- `environment.json`: Python/dependency information and CPU observations,
  including raw membership and mount inputs and observation errors.
- `discovery.log`, `discovery.json`, and `discovery-cleanup.json`: discovery
  output, the discovered method IDs, and the discovery cleanup record.
- `plan.json`: the plan, with each worker's methods and the CPU observations.
- `worker-N.log` and `worker-N.json`: each worker's log, and its method records
  and resource observations.
- `cleanup.json`: the worker cleanup record.

A zero worker exit without a complete result still fails the controller.
Discovery errors, duplicate IDs, missing or unknown execution, incomplete
methods, failed subtests, unexpected successes, changed tracked source, and
cleanup failures also fail the run.

The 80-minute command deadline (`--timeout-seconds`, default 4800) leaves room
inside the existing 90-minute job limit for cleanup and other owning checks.
SIGINT, SIGTERM, and timeouts fail the controller and clean its owned process
groups, including descendants whose worker leader exited. This is cooperative
test resource hygiene. A hard host kill can prevent reporting or artifact
upload; absent results never establish acceptance.

After a hard kill, preserve the first attempt's evidence and do not treat the
attempt as accepted. A retry must fit the actual grant and remaining allowance
of the task that owns the run. Ordinary retry authority remains usable when its
conditions hold; an explicit one-attempt or no-retry measurement grant requires
continuation by its allocator. A hard kill does not itself create a new
human-approval requirement
([coordination record](https://github.com/nisavid/provingkit/issues/120#issuecomment-6875642614)).

Report command elapsed time, method durations, summed test-process CPU including
waited-for children, and per-process peak RSS separately. Peaks are not summed
memory consumption. Hosted workflow elapsed and total occupied runner time come
from Actions job metadata; occupation is not billing. One run does not establish
variance or repeatability, and local timings are not matched hosted speedup.

## Change and qualify the schedule

Run `python -m unittest tests.test_run_provingkit_tests`, the complete command
in the selected mode above, the other owning source checks, `actionlint` on the
source workflow, and `git diff --check`. The disposable command fixtures exercise
failure and cancellation branches; they do not replace the real candidate suite. Review the
runner, workflow, tests, hints, and this procedure together on the same immutable
revision. Check required-status continuity and fixture isolation when the suite
changes. Return the candidate, local results, review evidence, and expected
runner use to Provingkit Dispatch, the accepted Preview successor, before any
hosted allocation or landing.

That coordination follows the operation. It applies to changing or qualifying
the schedule, whichever effort initiates it
([coordination record](https://github.com/nisavid/provingkit/issues/120#issuecomment-6875642614)).
Running the unchanged schedule for an ordinary pull request follows that task's
existing acceptance and allocation route. Existing resource and task limits
remain in force.

The regression suite keeps native two-worker command checks alongside serial
checks. A host with unknown capacity can run the serial and synthetic selector
checks explicitly with
`python -m unittest tests.test_run_provingkit_tests.SerialProvingkitTestExecutionTests tests.test_run_provingkit_tests.SyntheticCapacitySelectionTests`.
The synthetic observations establish scheduling branches only; they do not
attest the host's capacity. Keep blocked native two-worker checks visible and
run them on an environment with complete capacity observations before claiming
parallel qualification. Serial success does not turn their failures into skips.
