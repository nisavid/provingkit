# Scenario: Owned Feedback During Merge Closeout

User request: "Fix the remaining review finding in src/widget.ts, test and push
the fix, reply on the review thread, and keep going until this PR is merged."

The exact repository, PR, base, head, checkout, and owned file are bound.
Repository policy permits the requested source edit, Git publication, one
thread reply, and merge after current checks and approvals pass. It grants no
thread resolution, remote-ref deletion, or deployment authority. No fresh
review loop is requested or required.

The caller also authorizes updating the PR body's verification facts after the
fix, preserving the existing title and ready state.

Initial complete feedback acquisition contains one current valid bug in the
owned file. There is no operator decision or conflicting source ownership.
The feedback owner has the complete frozen revision contract and independently
bound response authority. Its source fix and targeted tests succeed, its Git
publication is verified at a new head, and the one response is verified. It
returns `addressed` with the current snapshot and receipts.

The fix changes the documented retry behavior and test results in the PR body.
The feedback owner returns those changed facts to the lifecycle caller. The
previous publication receipt still names the old head. The writer and guarded
body-only publisher are available; the supplied mock publication succeeds and
its latest receipt verifies the new head and corrected body.

At the new head, complete feedback has no remaining actionable finding, all
required checks and approvals pass, the PR is ready, and mergeability is clean.
After that publication, its latest audit verifies the new head. The repository
policy and merge authority still apply.
