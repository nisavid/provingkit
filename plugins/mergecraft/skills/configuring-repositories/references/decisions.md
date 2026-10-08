# Choose controls from the desired behavior

Use these starting choices to explain a recommendation. They are conditional
associations, not fixed profiles to apply wholesale. Current target evidence,
applicable policy, and informed user choices govern the result.

| User concern or context | Useful starting choice | What makes it useful; what to establish |
| --- | --- | --- |
| A new repository or good defaults | Confirm owner/visibility and consequential controls as one coherent proposal | Visibility affects access, eligibility, and exposure. Infer project facts from contents; ask for unresolved purpose or access intent. |
| Protect the main integration branch | A PR path, useful required checks, and prevention of accidental deletion/force updates where supported | PRs preserve review context even with zero approvals. Establish recovery and bypass expectations; a rule's existence does not prove it governs the target. |
| One maintainer, agent-assisted work | A PR path with zero required approvals unless another eligible reviewer is established | An author cannot supply their own independent approval. Keep useful checks and optional review without promising an unavailable approving actor. |
| A team wants independent review | An appropriate approval count, reviewer ownership where useful, and protection against unreviewed later changes | Establish eligible actors, actual ownership patterns, and whether stale dismissal or last-push approval best fits the threat. Both impose different review costs. |
| Predictable history | Match permitted merge methods to the desired history and effective branch rules | Squash can preserve one change per PR; rebase preserves individual commits. Linear history and queue requirements can constrain the choice. Respect project policy. |
| Faster safe integration | Select useful checks, then consider strict freshness or a merge queue | Freshness tests the change against the current base and can require reruns. Queues need their own event/check coverage and may be unavailable in the target plan. |
| Extensive CI hardening | Stack/layout-appropriate analysis, content validators, least privilege, and gates backed by observed producers | Map the specific threat to detection and enforcement. More checks alone do not establish useful coverage or safe privileged execution. |
| An unusual setup or freeze | Explain consequential tradeoffs and implement an informed choice within applicable policy | An intentional freeze is valid. Missing required actors or results can create an unintended freeze; settle material intent rather than silently removing protection. |
| Existing Terraform/App configuration | Change its maintained source or use its supported operation | A competing direct write can be reverted or create drift. A writer transition requires the user's choice and a preservation plan. |

Connect the requested control to its supporting conditions. For example,
“Require CI” implies a stable result identity, coverage of the relevant events
and paths, and a way to observe enforcement. “Require CODEOWNERS” implies a
valid ownership file, eligible owners, and coverage of the files of concern.
“No additional spend” implies verified account controls and allowance, not
merely a timeout or alert. The detailed guides provide the GitHub-specific
premises; refresh those premises before relying on them.

When assessing existing configuration, identify what it accomplishes, what
cannot yet be established, and the smallest useful change. Preserve deliberate
choices even when they differ from a recommended starting point. Do not widen
a focused task into adopting every suggestion in this table.
