# Run complete Provingkit contract methods

Use this procedure to run, change, or diagnose the two-worker source-contract
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

   The runner requires an observed capacity of at least two CPUs, bounded by
   affinity and every visible ancestor cgroup quota. Missing observations or
   insufficient capacity fail before test workers start. The fixed budget is
   one runner and at most two simultaneous complete-method test workers.
3. Require exit status zero, `result.json` with `successful: true`, both worker
   reports and logs, and successful cleanup records. Every discovered method
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
Longest-first allocation balances the workers while retaining discovery order
inside each worker. New methods receive the longest current estimate; obsolete
hint names are ignored. Hints never define coverage or acceptance. The initial
estimates come from the accepted
[serial measurement](https://github.com/nisavid/provingkit/actions/runs/35374474769).
Updating estimates requires complete successful current-run records and review;
there is no dependency on a frozen source, prior hosted run, or experiment branch.

## Diagnose and retain execution

Keep the complete output directory for failed as well as successful runs. It
contains discovery, plan and CPU observations, Python/dependency information,
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

Report command elapsed time, method durations, summed test-process CPU including
waited-for children, and per-process peak RSS separately. Peaks are not summed
memory consumption. Hosted workflow elapsed and total occupied runner time come
from Actions job metadata; occupation is not billing. One run does not establish
variance or repeatability, and local timings are not matched hosted speedup.

## Change and qualify the schedule

Run `python -m unittest tests.test_run_provingkit_tests`, the complete command
above, the other owning source checks, `actionlint` on the source workflow, and
`git diff --check`. The disposable command fixtures exercise failure and
cancellation branches; they do not replace the real candidate suite. Review the
runner, workflow, tests, hints, and this procedure together on the same immutable
revision. Check required-status continuity and fixture isolation when the suite
changes. Return the candidate, local results, review evidence, and expected
runner use to the preview coordinator before any hosted allocation or landing.
