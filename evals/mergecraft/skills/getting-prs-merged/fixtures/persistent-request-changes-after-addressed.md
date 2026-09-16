# Scenario: Requested Changes After Completed Author Work

The caller authorized fixing feedback within `src/widget.ts`, verifying and
publishing that work, replying once per authorized finding, and merging after
all gates pass. Approval and review-thread resolution belong to the reviewer.
No authority to dismiss reviews or resolve the reviewer's threads was supplied.

The feedback owner returned `addressed` at head H2. Its existing result includes
the accepted finding F1's exact source identity and revision R1, its disposition
and source/head binding, verified fix and Git publication, and one verified
response receipt. A complete post-fix acquisition at H2 supports those bindings.
There is no ambiguous provider result or pending author-side action.

Each case below is an independent later complete acquisition. Required checks
and canonical publication audit pass at H2 unless a case says otherwise.

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
