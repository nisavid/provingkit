# Run complete Provingkit contract methods

Use this procedure to run, change, or diagnose the complete source-contract
schedule. The production consumer is the **Provingkit source boundary** job in
`.github/workflows/provingkit-source.yml`; the command and its regression suite
are `scripts/run_provingkit_tests.py` and `tests/test_run_provingkit_tests.py`.
Other member checks and the standalone source validator keep their own routes.

## Run the candidate

1. Use a Linux checkout with complete Git history and the retained refs required
   by `tests.test_validate_provingkit`. Keep its tracked files and borrowed Git
   object store unchanged for the run. Use the workflow's Python and dependency
   versions for a hosted comparison. Record the candidate commit and whether
   local validation differs from that environment, including pytest presence.
2. Read this procedure from that candidate revision. Run the command with a new
   output directory outside the candidate:

   ```sh
   python scripts/run_provingkit_tests.py . --output-dir /tmp/provingkit-tests
   ```

   The default `--workers 2` requires an observed capacity of at least two CPUs,
   bounded by affinity and every visible ancestor cgroup quota. Missing
   observations or insufficient capacity fail before test workers start.
   For local functional validation, explicitly select serial execution when
   capacity is unknown or insufficient for two workers:

   ```sh
   python scripts/run_provingkit_tests.py . --workers 1 --output-dir /tmp/provingkit-tests-serial
   ```

   Serial execution retains CPU observations, errors, and unknown capacity;
   it makes no minimum-capacity claim. The host scheduler and quotas govern
   execution. The fixed budget is one controller and the selected one or two
   complete-method test workers, with their ordinary descendants. Serial mode
   does not impose a one-CPU utilization cap or extend the deadline.
3. Require exit status zero, `result.json` with `successful: true`, the selected
   `worker_count` in the plan and result, all selected worker reports and logs,
   and successful cleanup records. Every discovered method
   must appear exactly once with a completed outcome. Inspect method and subtest
   skips and their reasons; a skipped optional dependency remains a missing
   runtime observation. Complete the standalone validator, projection, prepared
   entrypoint, exclusion, member, artifact, and derived-lock checks in the source
   workflow before claiming source acceptance.

The controller discovers the current module in a separate process. Each worker
rediscovers the full module before selecting its assigned whole methods. Every
assertion and subtest stays inside its method. Mutable fixtures use separate
worker temporary directories and the existing per-test temporary clones; only
the candidate source and its Git objects are shared. New tests must preserve
that isolation. Review any new shared module/class fixture before using this
schedule.

`scripts/provingkit_test_timings.json` supplies advisory duration estimates.
With two workers, longest-first allocation balances their assignments while
retaining discovery order inside each worker. Serial execution puts every
method in one worker in discovery order. New methods receive the longest current
estimate; obsolete hint names are ignored. Hints never define coverage or
acceptance. The initial estimates come from the accepted
[serial measurement](https://github.com/nisavid/provingkit/actions/runs/35374474769).
Updating estimates requires complete successful current-run records and review;
there is no dependency on a frozen source, prior hosted run, or experiment branch.

## Diagnose and retain execution

Keep the complete output directory for failed as well as successful runs. It
contains discovery, plan and CPU observations (including raw membership and
mount inputs and observation errors), Python/dependency information,
tracked-source snapshots, worker logs and method records, resource observations,
and cleanup records. CI retains these for 30 days. A zero worker exit without a
complete result still fails the controller. Discovery errors, duplicate IDs,
missing or unknown execution, incomplete methods, failed subtests, unexpected
successes, changed tracked source, and cleanup failures also fail the run.

The 80-minute command deadline leaves room inside the existing 90-minute job
limit for cleanup and other owning checks. SIGINT, SIGTERM, and timeouts fail the
controller and clean its owned process groups, including descendants whose
worker leader exited. This is cooperative test resource hygiene. A hard host
kill can prevent reporting or artifact upload; absent results never establish
acceptance. Retry only through the owning task's allocation policy, preserving
the first attempt's evidence.

A successful serial run establishes complete local functional execution only
when coverage, outcomes, source stability, and cleanup all pass. It does not
qualify the two-worker schedule or parallel fixture isolation, establish hosted
timing, or replace required production status checks. An unknown CPU capacity
remains unknown after a successful serial run.

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
runner use to the preview coordinator before any hosted allocation or landing.

The regression suite keeps native two-worker command checks alongside serial
checks. A host with unknown capacity can run the serial and synthetic selector
checks explicitly with
`python -m unittest tests.test_run_provingkit_tests.SerialProvingkitTestExecutionTests tests.test_run_provingkit_tests.SyntheticCapacitySelectionTests`.
The synthetic observations establish scheduling branches only; they do not
attest the host's capacity. Keep blocked native two-worker checks visible and
run them on an environment with complete capacity observations before claiming
parallel qualification. Serial success does not turn their failures into skips.
