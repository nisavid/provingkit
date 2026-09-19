# Correct one missing timing estimate

Offline allocation analysis predicts about three minutes of improvement from correcting one missing duration hint in the two-worker command. I recommend qualifying a one-entry hint addition before considering a complete refresh.

I compared [main run 35409128973](https://github.com/nisavid/provingkit/actions/runs/35409128973) with [PR run 35404033390](https://github.com/nisavid/provingkit/actions/runs/35404033390), using the [published runner and procedure](https://github.com/nisavid/provingkit/tree/89d895269db5652aafa9ff9a642114585e7bb709). Both runs have identical snapshots of all 763 tracked files, identical retained refs, complete Git history, identical recorded environments, and the same ordered discovery of 95 unique methods. Both completed 94 successful methods, one method skipped because pytest was unavailable, and 146 successful subtests. Source snapshots remained unchanged during execution, and cleanup succeeded.

The 94-entry hint file omits `test_source_boundary_runs_complete_methods_with_the_other_owning_checks`. That method therefore receives the longest existing estimate, **455.037 seconds**, although its observed duration was **0.012715 seconds on main and 0.013102 seconds in the PR run**. This is an absent source-method hint, not a difference in discovered coverage or environment between these runs.

I reproduced the existing allocator exactly: descending estimate, method-ID tie breaking, least estimated worker load, method-count and worker-index tie breaking, then discovery order within each worker. The reconstructed current allocations match both retained plans.

All figures below are sums of observed method durations under hypothetical assignments; they are **not elapsed measurements of changed runs**.

| Hints trained on | Scored on | Current longer-worker total | Proposed longer-worker total | Predicted saving | Proposed worker gap |
|---|---|---:|---:|---:|---:|
| Main | PR, held out | 1,684.943 s | 1,505.677 s | 179.266 s | 1.394 s |
| PR | Main, held out | 1,686.288 s | 1,508.065 s | 178.223 s | 0.730 s |
| Main | Main, in sample | 1,686.288 s | 1,507.701 s | 178.588 s | 0.001 s |
| PR | PR, in sample | 1,684.943 s | 1,504.981 s | 179.962 s | 0.002 s |

Adding only the missing **0.013-second hint** predicts savings of **175.889 seconds on main** and **177.050 seconds in the PR run**, leaving worker gaps of 5.399 and 5.825 seconds. A complete refresh improves those predictions by only another 2–3 seconds.

The observed command durations were 1,686.825 and 1,685.462 seconds; the source-boundary jobs occupied their runners for 1,749 and 1,748 seconds. These measures must remain separate from hypothetical method totals. The allocator, original command, two-worker budget, assertions, and subtests remain fixed in this analysis.

The recorded environments match completely, including Python 3.13.15, all eight installed distributions, locale, affinity, and four effective CPUs. They do not establish identical CPU models, storage, host contention, or cache state. Checkout history also differs: main tested [`89d8952`](https://github.com/nisavid/provingkit/commit/89d895269db5652aafa9ff9a642114585e7bb709), while the PR tested merge checkout [`f96d38c`](https://github.com/nisavid/provingkit/commit/f96d38cb10020c34d16d69630ec8fe264f0bb498), combining [`42f79ec`](https://github.com/nisavid/provingkit/commit/42f79ecfb444b53079f55234a05f8eba6ba83cfc) with [`91af898`](https://github.com/nisavid/provingkit/commit/91af898ef72fce984a4843071e9fbf33cf878113). The retained checkout log establishes that distinction; the PR objects were unavailable for a complete offline ancestry comparison. Identical tracked files are therefore stronger evidence than identical history, which I cannot claim.

Across methods taking at least one second, main/PR duration ratios range from 0.981 to 1.025. Using unrounded instead of millisecond-rounded refreshed hints changes some assignments but shifts these predictions by less than 0.011 seconds. Neither sensitivity check addresses interference caused by changing concurrent method pairings. The one-entry proposal would lose its modeled saving if its resulting longer-worker total grew roughly 11.6–11.7% while the baseline stayed fixed.

The minimum next hosted allocation is **one ordinary validation cycle of a reviewed candidate that adds only the missing hint**, using the existing workflows and retention procedure. At this source revision, opening that candidate as a pull request starts four workflows and fourteen jobs, including one source runner with at most two whole-method workers, a 90-minute job limit, and the existing 80-minute command deadline. There is no source-only manual-dispatch route in the unchanged workflows. That run can establish the candidate’s observed allocation, coverage, and elapsed time. A performance or repeatability claim needs a separately authorized matched baseline/candidate comparison with repeated observations; these two unchanged-schedule runs cannot establish it.

This research supports [Can current duration estimates shorten the existing two-worker CI run?](https://github.com/nisavid/provingkit/issues/155). The [machine-readable analysis](2026-09-19-timing-estimate-analysis.json) preserves the complete proposed hint sets and hypothetical allocations. No candidate source or workflow was changed.

The [unapplied one-entry patch](2026-09-19-missing-timing-hint.patch) makes the proposed change concrete. Applying it, qualifying the candidate, and allocating hosted validation are subsequent steps; this research branch changes no active hints.
