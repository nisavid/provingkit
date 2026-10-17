# Zero required approvals can coexist with a blocking review

The public repository-configuration fixture reported a blocking requested-changes review with its required approval count set to zero. The approval count and existing review state are separate parts of the merge path. GitHub's [PR-rule documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-a-pull-request-before-merging) describes the effect of requested changes from reviewers with write access.

## Recorded request

On 2026-10-17, [public qualification PR 3](https://github.com/nisavid/provingkit-repo-config-public-qualification/pull/3) received one ordinary squash merge request for revision `44d0d00aeac99f0182b9871e3cf48fad45ec366a`, targeting `4876a2f967e59176650d72cabb4157e8c78e4eec`. The active ruleset had `required_approving_review_count: 0` and no bypass actors. Its required `fixture-ci` check failed at the deliberately mismatched resource heading; the neighboring analysis checks succeeded. A CodeRabbit requested-changes review was present.

The server returned “Repository rule violations found”. Immediate readbacks showed the PR open, both refs unchanged, and the ruleset unchanged. The response wrapper retained neither a numeric HTTP status nor a named violation.

## Provider evaluation

An authenticated read of [rule suite 4573919423](https://api.github.com/repos/nisavid/provingkit-repo-config-public-qualification/rulesets/rule-suites/4573919423) returned these active evaluations from ruleset `25285083`:

| Rule | Result | Detail |
| --- | --- | --- |
| `pull_request` | Fail | 1 review requesting changes by reviewers with write access. |
| `required_status_checks` | Fail | Required status check `fixture-ci` is failing. |
| `non_fast_forward` | Pass | No detail supplied. |
| `deletion` | Pass | No detail supplied. |

The suite's repository, actor, main ref, base revision, and timestamp correlate with the retained request observation within one second. The [API record](https://docs.github.com/en/rest/repos/rule-suites#get-a-repository-rule-suite) supplies no PR number, original fault-head field, or request identifier; the association is a correlation rather than a provider-issued request identity. Its `after_sha` is not evidence that the rejected update reached `main`.

Both review and CI failures were reported for that evaluation. The rejection does not isolate CI as its sole cause, and later success cannot establish that counterfactual. The [qualification checkpoint](https://github.com/nisavid/provingkit/issues/377#issuecomment-6230482123) retains the resulting method hold; this observation selects no revised acceptance criterion.

## Source-guidance comparison

A matched synthetic assessment compared the six-file `configuring-repositories` Skill from development commit `e50777edc12c17f5c5f1c4ede245c2a45064476a` with a prepared copy adding one explanation of requested-changes reviews beside the approval-count guidance. The request supplied both blockers and the relevant primary-documentation rule. Each condition used one fresh session, the same requested Daybreak Blue model at high effort, the same inspected general operator guidance, and disabled environment and tool access. The two source copies differed only in that guide paragraph; canonical source remains unchanged.

The [captured grading input](2026-10-17-review-gate-guidance/captured-input.json) retains the raw synthetic request, rubric, complete original responses, and attributed execution projections. A fresh independent grader received the outputs in randomized order with condition labels withheld. Its [unchanged grading artifact](2026-10-17-review-gate-guidance/captured-grade.json) awarded both responses six of six expectations, with no additional concerns.

| Output identity | Source condition | Passed expectations |
| --- | --- | --- |
| `output-b3dc4c2fcdd9` | Published development Skill | 6/6 |
| `output-a6eb8229398e` | Prepared explanatory addition | 6/6 |

Both responses identified the review and CI blockers, distinguished approval count from requested changes, preserved review and check authority, and called for fresh observations before a later operation. This case demonstrates no baseline correction, superiority, or causal benefit. Static plugin-eval analysis also reported no warnings or failures for either copy; that result is not behavior evidence.

The grader assessed response text and controller execution projections, not authenticated provider provenance or protection effectiveness. Complete provider traces and source bindings were checked locally. This is one source-supplied exploratory case, outside the twelve-case corpus; it establishes no native discovery, hosted effect, complete qualification, or release acceptance. The guide addition remains prepared for the later source join and still needs affected source review and owning checks before adoption. The fixture-method decision remains pending.
