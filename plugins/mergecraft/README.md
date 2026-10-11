# Mergecraft

Mergecraft is an Agent Plugins GitHub authoring and pull-request lifecycle
package with a native Claude adapter. It owns exact human-facing Issue and
pull-request body authoring, Issue–PR contribution ledgers and Development links,
reviewer navigation, guarded PR publication,
Graphite draft transport, feedback coordination and interaction, review
readiness, merge closeout, and stacked fixups.

Canonical PR publication requires every caller to select `required` or explicit
`not-required` review and its specialist inventory before invoking the writer
or freezing the candidate. The writer's ordinary independent review gate
accepts a verified bare `clean` Tricritical hand-back for the current title/body,
inputs, requirements, scopes, and evidence dependencies. `not-required` records
no witnessed provenance and does not waive that review. Callers preserve the
selection through publication, readiness, and resume. `required` adds the
authenticated Task Witness gate and remains unavailable without its separately
qualified integration. Task Witness is optional future equipment for callers
that need its stronger cross-harness evidence contract.

## Public skills

| Public skill | Responsibility |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| writing-github-issue-and-pr-markdown | Valid GFM and exact body bytes for seven human-facing GitHub fields, without actuation. |
| maintaining-issue-pr-relations | Evidenced bilateral contribution ledgers, cached closure settings, and guarded Development-link reconciliation. |
| writing-reviewable-pr-descriptions | Canonical title/body content and Stack/Diff navigation. |
| publishing-reviewable-prs | Standalone creation, exact title/body/draft-ready actuation, historical ledger edits, and publication evidence/audit/reconciliation. |
| graphite | Graphite topology and temporary stacked draft transport. |
| addressing-pr-review-feedback | Feedback-outcome coordination across acquisition, adjudication, revision, checkpoint, and interaction owners. |
| interacting-with-pr-review-feedback | One authorized typed-source response through the inline or PR conversation actuator, with durable replay and reconciliation. |
| resuming-reviewed-prs | Exact target recovery and selection of the next lifecycle owner. |
| getting-prs-ready-for-review | Review-readiness outcome coordination. |
| getting-prs-merged | Merge outcome coordination through the internal merge actuator. |
| stacking-pr-fixups | Narrow fixup branches and stacked fixup PR coordination. |

There are no compatibility routers and no public PR-creation orchestrator.
Semantic sibling links remain relative within this plugin. Cross-plugin calls
use qualified identities.

## Issue–PR relations

Relation maintenance applies to new contributions, material contribution or
completion-scope changes, explicit repairs, and applicable merge consequences.
Unchanged intent and unrelated edits skip acquisition. Both bodies retain all
verified contributions using stable links and useful role annotations, without
copied titles or status. Native Development links follow the Issue repository's
closure policy and available capacity; they are not a one-to-one relation.

Partial contributions need a usable observation that auto-close is disabled.
Otherwise, native links require evidence that the triggering merge satisfies
the Issue's completion gates. The setting cache reuses an observation throughout
the task, including resumes, and defaults to 30 days across tasks, with optional
no expiry. Cache hits retain the original timestamp. Explicit refresh, a newly
observed change, or contradictory behavior invalidates affected plans. No
setting changes occur during installation or ordinary relation handling.

The [relation contract](skills/maintaining-issue-pr-relations/references/relation-contract.md)
defines evidence, state-read budgets, disclosure, capacity, and recovery.
The public helper returns finite plans and verifies individually authorized
effects. It never closes or reopens Issues. Existing PR ledger edits use the
[bounded publication mode](skills/writing-reviewable-pr-descriptions/references/relation-ledger.md),
which preserves title, state, and unrelated bytes even when branches no longer
exist. Its receipts establish only those edits; canonical publication and
readiness retain their own gates.

## Package validation

From the package root:

    python3 skills/writing-reviewable-pr-descriptions/scripts/validate_change_navigation.py --help
    python3 skills/writing-reviewable-pr-descriptions/scripts/validate_relation_ledger.py --help
    python3 skills/publishing-reviewable-prs/scripts/create_reviewable_pr.py --help
    python3 skills/publishing-reviewable-prs/scripts/update_reviewable_pr.py --help
    python3 skills/publishing-reviewable-prs/scripts/audit_reviewable_pr.py --help
    python3 skills/publishing-reviewable-prs/scripts/publish_relation_ledger.py --help
    python3 skills/maintaining-issue-pr-relations/scripts/relation_state.py --help
    python3 skills/graphite/scripts/submit_draft_stack.py --help
    python3 skills/getting-prs-merged/scripts/post_coderabbit_comment.py --help
    python3 skills/addressing-pr-review-feedback/scripts/review_feedback_state.py --help
    python3 skills/interacting-with-pr-review-feedback/scripts/response_cli.py --help

## Developing this plugin

This section is for people who want to contribute to Mergecraft, fork it, or
work with its internals. An installed copy leaves out the topology
(`topology.json`), the evaluation corpora, the validator, and the tests; they
stay in the source repository. The
[developer page](https://github.com/nisavid/provingkit/blob/main/plugins/mergecraft/DEVELOPING.md)
describes the source layout, the Markdown authoring projections, the operation
registry, repository release validation, and the evaluation evidence.
