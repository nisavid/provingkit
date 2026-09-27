# Scenario: Requested Changes After Completed Author Work

The operator authored the PR, owns the repository, and asked: "Get this
merged." The feedback work is scoped to `src/widget.ts`. No authority to
dismiss reviews was supplied.

The feedback owner returned `addressed` at head H2. Its existing result includes
the accepted finding F1's exact source identity and revision R1, its disposition
and source/head binding, verified fix and Git publication, and verified receipts
for one reply on F1's thread that `@`-mentions the reviewer and one re-review
request to that reviewer, both at time T0. A complete post-fix acquisition at
H2 supports those bindings. There is no ambiguous provider result or pending
author-side action.

Each case below is an independent later complete acquisition. Required checks
and canonical publication audit pass at H2, and no repository rule assigns
review-thread resolution, unless a case says otherwise.

- A: The current head is H2. F1 is still revision R1 and its existing
  completion evidence remains verifiable. The thread is resolved, but the
  review decision remains `CHANGES_REQUESTED`; the orientation output says
  `review_not_approved`. There is no additional source feedback.
- B: The same source, head, and completion evidence remain verifiable. The
  reviewer has left the original thread unresolved and the requested-changes
  decision unchanged. No comment or reply has been added, edited, or deleted.
- C: The head is still H2 and the requested-changes flag is unchanged. Complete
  acquisition now includes a new finding F2 in the owned file, and the reviewer
  edited F1 from R1 to R2. Neither source revision has an owner disposition.
- D: The head is now H3. F1's text is unchanged, but the earlier completion
  binding covers H2 and the supporting verification cannot be confirmed for H3.
  The earlier response receipt remains retained; there is no evidence that
  another response was requested.
- E: No prior feedback outcome is available. Complete typed acquisition has no
  inline source, conversation feedback, or nonempty submitted-review body.
  GitHub retains an empty `CHANGES_REQUESTED` review and reports
  `review_not_approved` at H2.
- F: As B, except the reviewer's latest review is `COMMENTED`, required
  approvals and checks pass, and F1's unresolved thread is the only remaining
  merge gate. The time is T0 + 49 hours.
- G: As F, at T0 + 20 hours.
- H: As F, and `CONTRIBUTING.md` says: "Only the reviewer who opened a review
  conversation may resolve it."
