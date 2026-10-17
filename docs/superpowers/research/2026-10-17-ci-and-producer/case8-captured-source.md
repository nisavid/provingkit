# Correction and verification proposal

Using `configuring-repositories`, I’d treat this as an incomplete producer migration, not a renamed check.

## Assessment

The supplied records establish three distinct gaps:

- `p1` does not satisfy the current requirement. The rule is bound to App 77, while the recorded check came from App 15368. Its `skipped` conclusion also proves no quality work ran; GitHub may treat a conditionally skipped job as successful, but that is not validation.
- `p2` has no `quality` result because the workflow-level `src/**` filter prevents the workflow from starting.
- `g1` has no result because `pull_request` and `push` do not cover merge-queue commits. GitHub Actions requires the separate `merge_group` event.

The existing readiness result is stale because both producer identity and queue behavior changed after it was cached. No causal merge-gate behavior has been demonstrated.

## Smallest useful correction

Change only the workflow that produces `quality` and that requirement’s app binding:

1. Make `quality` unconditional for every PR targeting `main`:
   - Remove the `startsWith(github.head_ref, 'code/')` job condition.
   - Remove `paths: src/**` from the `pull_request` event.
   - Run the existing quality work even for documentation-only changes. That is simpler and safer than adding a second aggregation job merely to preserve selective execution.

2. Add merge-queue coverage:

   ```yaml
   on:
     pull_request:
       # Preserve existing branch targeting, but no paths filter.
     merge_group:
       types: [checks_requested]
     push:
       # Preserve existing push behavior.
   ```

3. After a candidate workflow revision produces a real, non-skipped `quality` run from App 15368, replace the required check binding:

   ```json
   {
     "context": "quality",
     "app_id": 15368
   }
   ```

   Preserve the current strictness value and every unrelated required check when updating the rule; the REST operation replaces supplied check collections rather than expressing an isolated rename.

4. Coordinate the cutover because the dead App 77 requirement may prevent the workflow change itself from landing:
   - Qualify the candidate workflow on its PR first.
   - Pause other merges and queue use.
   - Change the binding to App 15368.
   - Land the reviewed workflow change through the normal one-approval, squash-only route.
   - Resume queue use only after merge-group coverage is qualified.

Do not change the one-review requirement, squash-only history, bypass actors, or queue selection.

## Bounded verification

No part of this design has been run against the repository.

### Before changing the binding

Read back the effective rule and retain its complete preimage, including strictness, all required checks, approval count, bypass state, allowed merge methods, and any inherited enforcement. Confirm which maintained writer owns these settings.

Independently review the final workflow revision. Then obtain hosted evidence from its PR revision:

| Case | Required evidence |
|---|---|
| Workflow-only or README change from a branch not beginning with `code/` | A `quality` run is created by App 15368, is not skipped, targets the PR revision, and its logs show the quality command executed. |
| `src/**` change | The same result is created and executes the quality command. |

A matching name alone is insufficient; record the app, revision, event, conclusion, and executed work.

### After the coordinated cutover

1. Read the rule back and confirm that only `quality`’s producer binding changed from App 77 to App 15368.
2. Confirm one approval is still required, no bypass was added, and squash remains the only merge method.
3. Submit an authorized disposable PR to the queue and inspect its merge-group commit:
   - `quality` must be created for the merge-group SHA by App 15368.
   - It must execute rather than report `skipped`.
4. For causal enforcement evidence, keep every neighboring gate satisfied and use no bypass:
   - Make a controlled `quality` failure and observe rejection attributable to that result.
   - Restore the passing revision, ensure it has a valid approval, and observe that the gate allows the next step.
   - A full queue acceptance test can result in an automatic merge, so it requires separate authorization for queue submission and that merge outcome. Without it, report only producer and event coverage, not end-to-end queue enforcement.

Finally, discard the cached readiness verdict and have its owner reassess against the final workflow revision, App 15368 binding, effective rules, and queue evidence.