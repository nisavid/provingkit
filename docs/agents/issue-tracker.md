# Issue tracker: GitHub and Linear

Create issues and specs in the intended GitHub repository. Verify the synchronized Linear issue before managing its lifecycle there. Establish the exact pair from an integration-authored linkback or equivalent native synchronization metadata, and record both stable issue identities for readback. A matching title or user-posted URL alone does not establish the pair; hold dependent writes when evidence is missing, conflicting, or inaccessible. Use GitHub directly where needed, then read both representations back; a write or synchronization request alone does not establish the resulting state. If the counterpart or synchronization is missing or ambiguous, preserve the issue identity and reconcile the discrepancy before a dependent change.

## Work-cycle checkpoints

At intake, read the current issue, applicable triage guidance, and the relevant map and dependencies. Identify the authorized outcome, current owner and grant, remaining work, and any hold. For work governed by ordinary issue triage, at intake, dispatch, and reentry consume the current triage result or a recorded authorized exception for the proposed work. For Wayfinder decision tickets, use the Wayfinding operations below to assess the map, dependencies, custody, and authority; do not require ordinary triage labels. Find the applicable decision or maintainer override in the issue record and verified counterpart; check that it covers the proposed outcome and scope and that no later decision, material change, or hold supersedes it. Reuse an assessment that still applies; reconcile a missing or stale result before dependent work. A pending decision holds only the work that needs it, while independent authorized work may continue. Use current state rather than an old label or handoff to decide the next action. Tracker assignees identify the responsible person; they do not identify an agent session, grant authority, or prove active worker custody. Use the coordinator’s accepted allocation to identify the worker and its obligations.

Manage supported state, assignment, project, milestone, and dependency changes in Linear, verifying the corresponding GitHub representation as applicable. Keep distinct issues and efforts distinct. Before retrying an uncertain write, read the authoritative result and reconcile the operation; do not assume either failure or success. Respect existing human decisions, holds, and source ownership. For Wayfinder, preserve the GitHub-native graph used by its frontier: use Linear for supported lifecycle changes and make a targeted GitHub write when the required GitHub representation is missing. Read back both trackers before relying on custody or the frontier. GitHub commands below are targeted operations, not a substitute for the Linear lifecycle route.

At a checkpoint or handoff, record the completed result and its evidence, unresolved obligations, current owner, next authorized action or hold, and the return condition. Choose the audience before recording a checkpoint: GitHub-synced comments must be suitable for GitHub; keep private details in a verified private surface. The receiving coordinator consumes the complete applicable return and verifies both tracker representations. For a custody transfer, keep the current accountable owner until the authorized receiver accepts the outstanding work; existing applicable acceptance suffices. Record the accepting worker and the outstanding obligations in the coordinator’s existing allocation for the issue. Change tracker fields only when the authorized facts they represent change. Keep the assignment when the responsible person stays the same. For an authorized change of responsible person, update the assignment through the Linear lifecycle route. Verify the updated allocation and both tracker representations before relying on the transfer. A completed child or delivered handoff does not close an unfinished parent; preserve its accountable owner and continuation. Close only when the authorized outcome and applicable closeout requirements are satisfied.

Use `capturing-agent-procedures` when maintaining or consuming this procedure. When dispatching tracker work, the dispatcher supplies the reviewed revision and the condition for its use. The dispatcher, worker, and receiving coordinator load and record the reviewed revision before relying on it, and distinguish actual tracker readback from constructed examples. See [triage labels](triage-labels.md) for the ordinary triage label mapping.

For Linear release records and release notes, use
[release reconciliation](linear-release-reconciliation.md) after publication,
after release content or scope changes, and when correcting stale records.
That release workflow preserves this contract's GitHub issue creation and Linear lifecycle routing.

## GitHub operations

Use these operations for GitHub issue creation, reading, and targeted changes. Reconcile lifecycle changes with the corresponding Linear issue as described above.

Set `$issue_repo` to the intended repository on `github.com` as `owner/repo` and `$n` to the issue number. Resolve the pair from the task, verified issue URL, or repository-qualified reference. If the reference leaves the repository ambiguous, resolve it before reading or writing. Check the returned issue URL against the pair before using the read to verify the Linear counterpart.

Use `--repo "github.com/${issue_repo:?}"` with numbered issue commands and repository-wide operations, or use the verified issue URL as the target of an issue command that accepts a URL. For a numbered mutation, bind and require both the verified repository and number, or use the verified issue URL that identifies both. Use `gh api --hostname github.com` for REST and GraphQL. In REST paths, interpolate the verified repository directly. In GraphQL queries, pass its owner and repository name as variables. Apply this convention regardless of the checkout, `GH_HOST`, or `GH_REPO`. Compare GitHub owner and repository names case-insensitively and match issue numbers exactly. The shell's `:?` rejects an unset or empty variable before running the command.

- **Create an issue** with `gh issue create --repo "github.com/${issue_repo:?}" --title "..." --body "..."`. Use a heredoc for multi-line bodies.
- **Read an issue** with `gh issue view "$n" --repo "github.com/${issue_repo:?}" --json number,url,title,body,state,assignees,comments,labels --jq '{number, url, title, body, state, assignees: [.assignees[] | {id, login}], labels: [.labels[].name], comments: [.comments[] | {author: .author.login, body, url}]}'`. Retain comment authorship and issue identity when verifying the synchronized counterpart. `--comments` prints human-readable text and carries no labels, so it cannot feed `jq`.
- **List issues** with `gh issue list --repo "github.com/${issue_repo:?}" --state open --limit 500 --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'` and appropriate `--label` and `--state` filters. `gh issue list` returns 30 by default, so always pass `--limit` and raise it rather than reading a truncated page.
- **Comment on an issue** with `gh issue comment "${n:?}" --repo "github.com/${issue_repo:?}" --body "..."`.
- **Apply or remove labels** when a targeted GitHub operation is needed. Use `gh issue edit "${n:?}" --repo "github.com/${issue_repo:?}" --add-label "..."` or `gh issue edit "${n:?}" --repo "github.com/${issue_repo:?}" --remove-label "..."`.
- **Close an issue** when a targeted GitHub operation is needed after the Linear lifecycle update. Use `gh issue close "${n:?}" --repo "github.com/${issue_repo:?}" --comment "..."`.

## Pull requests as a triage surface

**PRs as a request surface: no.** _(Set to `yes` if this repo treats external PRs as feature requests; `/triage` reads this flag.)_

When set to `yes`, PRs run through the same labels and states as issues. Set `$pr_repo` to the verified PR repository and use the same repository convention.

- **Read a PR** with `gh pr view "$n" --repo "github.com/${pr_repo:?}" --comments` and `gh pr diff "$n" --repo "github.com/${pr_repo:?}"`.
- **List external PRs for triage** with `gh api --hostname github.com "repos/${pr_repo:?}/pulls?state=open&per_page=100" --paginate --jq '[.[] | {number, title, author_association}]'`. Keep PRs whose `author_association` is `CONTRIBUTOR`, `FIRST_TIMER`, `FIRST_TIME_CONTRIBUTOR`, or `NONE`.
- **Comment, label, or close** with `gh pr comment`, `gh pr edit --add-label` or `--remove-label`, or `gh pr close` and the same `--repo "github.com/${pr_repo:?}"`.

GitHub shares one number space across issues and PRs. To identify the item, try `gh pr view "$n" --repo "github.com/${pr_repo:?}"` in the intended repository, then use **Read an issue** with that same repository if the number belongs to an issue.

## When a skill says "publish to the issue tracker"

Create a GitHub issue.

## When a skill says "fetch the relevant ticket"

Resolve the GitHub repository and issue number, then follow [GitHub operations](#github-operations) for the verification read, retaining the issue URL and comment authorship. Verify and read its Linear counterpart for applicable workflow state, decisions, and holds; consult GitHub for public discussion and native relations. If a required source is inaccessible or the records disagree, resolve the gap before relying on the affected decision.

## Wayfinding operations

Used by `/wayfinder`. In this repository, load and apply this contract at the Wayfinder entrypoint and in the coordinator’s dispatch. Its frontier eligibility, allocation, and resolution steps govern when they differ from the generic skill, before filtering candidates: preserve an accepted allocation without a redundant assignment write, and verify the map pointer before closing the child. The **map** is a single issue with **child** issues as tickets.

A child or blocker can belong to another repository of the same owner, and two of them can share a number. Carry each verified `owner/repo` and number together through discovery, reconciliation, allocation, and resolution. Use the [GitHub operations convention](#github-operations) with `$map_repo` and `$map` for the map, `$child_repo` and `$child_number` for a child, and `$blocker_repo` and `$blocker` for a blocker. Bind `$child_repo` and `$child_number` together from the verified child identity. When using **Read an issue** for a child, use that pair as the repository and number. In an issue body, a bare `#<n>` names an issue in that body's repository. Use `owner/repo#<n>` for a reference to another repository.

- **Map**. Create a single issue labelled `wayfinder:map`, holding the Notes / Decisions-so-far / Fog body. Use **Create an issue** with `$map_repo` as `$issue_repo` and add `--label wayfinder:map`. Verify the created issue against the intended repository and retain its repository-qualified identity in the work record.

  **Establish the map’s governing order** before attachment or frontier selection. For a verified new map with no attachment history, choose native sub-issue order when native sub-issues are confirmed available for the map, or task-list order when they are confirmed unavailable. Retain the choice with the verified map identity in the work record for the first attachment and subsequent reads. For an existing map, preserve its established order even when the other representation is available. Hold if the evidence leaves the map’s attachment history or governing order unclear, or if the capability check for a new map is inconclusive.
- **Child ticket**. Use the same create-and-attach procedure whether the child is in the map repository or another repository of the same owner.

  - **Identify the child**. For a new child, use **Create an issue** with `$child_repo` as `$issue_repo` and add the label for its ticket type with `--label "wayfinder:${child_type:?}"`. Set `$child_type` to one of `research`, `prototype`, `grilling`, or `task`. Verify the returned URL against the intended repository, bind `$child_number` from it, and retain the verified `$child_url` and repository-qualified number in the work record before attempting attachment. If the create response is lost or ambiguous, reconcile whether creation succeeded before attempting another create. For an existing child, use **Read an issue**, verify the returned URL against `$child_repo` and `$child_number`, and apply **Verify the child type** before proceeding.
  - **Verify the child type** on the verified GitHub issue. Require exactly one supported type label from **Identify the child**.
  - **Reconcile the current parent** before either attachment route writes or declares the attachment complete, and before either frontier relies on membership. Read the verified child and requested map. Read the child's native parent wherever that relation is available, including when the requested map uses a task list:

    ```sh
    : "${child_repo:?}"
    gh api --hostname github.com graphql -f owner="${child_repo%%/*}" -f repo="${child_repo#*/}" -F number="${child_number:?}" -f query='
      query($owner: String!, $repo: String!, $number: Int!) {
        repository(owner: $owner, name: $repo) {
          issue(number: $number) {
            number
            repository { nameWithOwner }
            parent { number repository { nameWithOwner } }
          }
        }
      }'
    ```

    Require a successful native read that identifies the child and includes the parent field. Use fallback evidence alone only when the native parent relation is confirmed unavailable for the child. Hold a failed or ambiguous applicable read.

    Check the child's `Part of` line and the requested map's checklist. Verify any other map identified by the line or by an earlier attachment record, and check its checklist for the child. For an existing child without a `Part of` line, use the retained attachment record or verified checklist evidence to resolve any earlier attachment, including a checklist-only attachment. An empty checklist on the requested map cannot establish that an existing child is unattached.

    Compare parents by repository and number together. Hold if any evidence identifies a different parent, any relevant issue body cannot be verified, or the references or attachment history leave parentage unresolved. Duplicate matching references are ambiguous.

  - **Verify membership in the map's order** after reconciling the current parent. Follow **Establish the map’s governing order**. Native order requires the map's `subIssues` to list the verified child and the child's native parent to identify the map. Hold if either native read is inconclusive or those reads disagree about membership. Check all pages before treating the child as absent from `subIssues`. Task-list order requires the map's checklist to identify the verified child and the child's current `Part of` line to identify the map. When the governing representation verifies membership, the attachment is complete without a write.

    If membership is incomplete on a task-list map and exactly one fallback reference identifies the pair, repair that known partial attachment with its original map under existing authority using **Attach with a task list**. Start a new attachment through the map's governing route only when **Reconcile the current parent** establishes that the child is unattached. In all other cases of incomplete membership, hold the attachment for reconciliation.
  - **Attach as a native sub-issue** when the child is unattached and the map uses native sub-issue order. Resolve the child's numeric **database id**, then add it to the map with replacement disabled, including if a native parent is set between the read and the write:

    ```sh
    child_id=$(gh api --hostname github.com "repos/${child_repo:?}/issues/${child_number:?}" --jq .id) &&
      gh api --hostname github.com --method POST "repos/${map_repo:?}/issues/${map:?}/sub_issues" \
        -F sub_issue_id="${child_id:?}" -F replace_parent=false
    ```

    Reconcile the current parent and verify membership in the map's order again after the attempt. If the result is failed or uncertain, resume from the retained child identity and retry only if the shared checks establish the child is still unattached.

  - **Attach with a task list** on a map that uses task-list order, for an unattached child or a known partial attachment with that map.

    Write only missing references, in this order.

    1. Add `Part of owner/repo#<map>` at the top of the child body. Read it back and verify the map's repository and number before adding a checklist entry.
    2. Once the child's `Part of` line is verified, add the child's issue reference to the map checklist if it is missing. Use `#<child>` for a child in the map's repository and `owner/repo#<child>` for a child in another repository.

    Base each edit on the latest body and preserve its other content. After each write attempt, including a failed or uncertain result, reread both bodies and reconcile the current parent again. Retry only the missing reference. Verify membership in the map's order before declaring the attachment complete. Whole-body edits are last-writer-wins. A stale edit can remove a verified reference.
- **Blocking**. Reconcile the child's blockers before relying on frontier eligibility or making a dependency change. Apply the same check with either map order.

  - **Reconcile blockers**. Read the verified child and its current body, its verified Linear counterpart, and the governing decisions or earlier dependency records relevant to the child. Collect the GitHub native edges with **Read native blockers** wherever native dependencies are available. Collect every current `Blocked by:` reference, interpreting a bare `#<n>` in the child body's repository.
  - Read all incoming blocking relations of the verified Linear child, following all pages if the read is paginated. Verify that each relation identifies the related issue as the blocker and the verified child as the blocked issue. Resolve each Linear blocker to its verified GitHub counterpart. Treat an incomplete read or an unresolved endpoint, direction, or counterpart as unresolved evidence.
  - Combine the three sources by the blocker's verified GitHub repository and issue number, comparing repository names case-insensitively. Count each dependency once and retain every source that records it. For every blocker in the combined set, use **Read an issue** in its own repository, verify the returned identity, and establish its Linear counterpart. Compare GitHub and Linear states and use the governing decisions and verified tracker records to establish which edges still apply and whether each blocker is open, closed, or verified obsolete. A complete, empty read establishes absence only in that source. A verified open governing blocker excludes the child even when only one source records the edge. A verified obsolete reference does not exclude it. Hold a dependency change if unresolved evidence or an uncertain earlier write could affect that change. Hold ordered selection if the uncertainty could change which child is first.
  - **Add an authorized dependency** through Linear when supported. When the Linear edge is already verified, proceed directly to checking its required GitHub representation. Repair a missing GitHub representation only under existing authorization for that repair. If the required native GitHub edge is missing after synchronization, add it with `gh api --hostname github.com --method POST "repos/${child_repo:?}/issues/${child_number:?}/dependencies/blocked_by" -F issue_id="${blocker_id:?}"`, where `$blocker_id` is the blocker's numeric **database id** (`gh api --hostname github.com "repos/${blocker_repo:?}/issues/${blocker:?}" --jq .id`). Where native dependencies are confirmed unavailable, record the required GitHub dependency in a `Blocked by: #<n>, #<n>` line at the top of the current child body. Use `owner/repo#<n>` for a blocker in another repository.
  - **Remove an authorized dependency** through Linear when supported. After synchronization, reconcile any remaining GitHub evidence of the targeted edge. If an authorized cleanup is still needed, remove only the verified native edge or the matching reference from the current `Blocked by:` line, as established by reconciliation and covered by the authorization. If both record the edge, verify each and act only on the representations covered by the authorization. Preserve unrelated blockers, including same-number blockers in another repository, and preserve the rest of the body. An existing reference alone supplies no authority to migrate or remove a dependency.
  - Reconcile blockers again after each write attempt, including a failed or uncertain result, before retrying or relying on the resulting frontier. Treat a ticket as unblocked only when every governing blocker is confirmed closed or removed and no unresolved discrepancy can affect eligibility.
- **Frontier query**. Follow **Establish the map’s governing order** before reading the ordered children. Use the checklist for task-list order. For native order, use the query below. Verify the state, assignee, and blocker facts that affect eligibility.

  ```sh
  : "${map_repo:?}"
  gh api --hostname github.com graphql -f owner="${map_repo%%/*}" -f repo="${map_repo#*/}" -F map="${map:?}" --paginate --slurp -f query='
    query($owner: String!, $repo: String!, $map: Int!, $endCursor: String) {
      repository(owner: $owner, name: $repo) {
        issue(number: $map) {
          subIssues(first: 100, after: $endCursor) {
            pageInfo { hasNextPage endCursor }
            nodes {
              number
              repository { nameWithOwner }
            }
          }
        }
      }
    }'
  ```

  For each child in the ordered prefix, apply **Reconcile the current parent** and **Verify membership in the map's order** before relying on membership in either frontier. If the shared checks identify a known partial attachment on a task-list map, repair it only under existing authority and verify membership again. Hold the ordered selection if unresolved parentage or membership can affect which child is first, including a known discrepancy involving a child omitted from the governing order.

  `subIssues` returns children in map order. Consume the pages in order and keep each child's `repository.nameWithOwner` with its `number`. Resolve each task-list entry to the same pair.

  **Read native blockers** for the verified child whenever native dependencies are available. Query the child in its own repository and read all pages of its `blockedBy` connection:

  ```sh
  : "${child_repo:?}"
  gh api --hostname github.com graphql -f owner="${child_repo%%/*}" -f repo="${child_repo#*/}" -F number="${child_number:?}" --paginate --slurp -f query='
    query($owner: String!, $repo: String!, $number: Int!, $endCursor: String) {
      repository(owner: $owner, name: $repo) {
        issue(number: $number) {
          number
          repository { nameWithOwner }
          blockedBy(first: 50, after: $endCursor) {
            pageInfo { hasNextPage endCursor }
            nodes { number state repository { nameWithOwner } }
          }
        }
      }
    }'
  ```

  Verify the child identity on each page and retain every blocker's repository, number, and state. Hold if the applicable read fails, the identity or connection is ambiguous, or the pages are incomplete.

  Evaluate the ordered prefix before naming the first eligible child: verify each child's repository-qualified identity, read that issue in its own repository (**Read an issue** with `--repo "github.com/${child_repo:?}"`) and establish its Linear counterpart from it, apply **Reconcile blockers**, and reconcile the remaining lifecycle, custody, authority, and hold facts against the governing decisions and both tracker representations. Compare GitHub state and assignee identities from **Read an issue** with the verified Linear record wherever either field affects eligibility. Confirm an earlier exclusion that depends on a synchronized field.

  For ordinary frontier selection in either map order, require a child to be verified unassigned in GitHub and Linear. Skip a child with a verified assignee and verify the next child in order. Hold selection if an unresolved assignment discrepancy could change which child is first.

  Repair an authorized discrepancy or hold the ordered selection if the discrepancy can affect which child is first and remains unresolved. An earlier child whose identity, issue, or counterpart cannot be read or reconciled is not confirmed ineligible: hold the ordered selection at that child, and never evaluate an issue with the same number in another repository in its place. A stale GitHub blocker must not silently promote a later child. Skip a child confirmed ineligible, including one closed in Linear or already allocated, and verify the next candidate. Apply **Verify the child type** to each child still under consideration. Hold the ordered selection when an unresolved type could affect which child is first. A named independently authorized increment need not wait for an unrelated unresolved ordering decision. Do not mix the GraphQL `blockedBy` connection with REST `issue_dependencies_summary`.
- **Allocation and claim**: Continue an already accepted worker/coordinator allocation after checking its scope, current grant, relevant state, dependencies, and holds; preserve a correct assignment. A tracker assignee is not an exclusive agent-session claim, and readback does not make competing writes atomic. Autonomous initial self-claim for the dual-tracker, shared-account workflow is unresolved: do not rely on the prior GitHub claim command as a qualified route. Obtain an allocation through the existing coordinator or hold that claim until its route is selected and qualified. This limit does not prohibit independently authorized work with accepted custody.

- **Resolve**: `gh issue comment "${child_number:?}" --repo "github.com/${child_repo:?}" --body "$answer"`, then record a context pointer (gist + link) in the map's Decisions-so-far. Close through Linear only after verifying the entry as described below, then verify both tracker representations. If the required GitHub closure is missing after synchronization, use `gh issue close "${child_number:?}" --repo "github.com/${child_repo:?}"` as a targeted operation and recheck both.

  **Reconcile decision entries**. Use **Read an issue** with `$map_repo` and `$map` to read the current map body. Scan the entire body for entries with a decision marker or a decision context pointer, including pointers without markers. Resolve each available marker and pointer independently so either can identify a candidate for the target child. A qualified marker (`<!-- decision:owner/repo#<number> -->`) supplies the repository and number. A legacy marker (`<!-- decision:<number> -->`) supplies the number and relies on the pointer for the repository. A bare issue reference in a pointer is relative to the map's repository. Compare repository names case-insensitively and issue numbers exactly.

  For every entry whose marker or pointer identifies the target child, verify the pointer against the GitHub issue it identifies and require it to agree with the marker. A legacy entry whose pointer verifies a distinct child with the marker's number belongs to that child. Preserve entries verified to identify a distinct child. Hold append and close and return the conflict to the coordinator if a target entry has a missing or conflicting pointer or marker, lies outside Decisions-so-far, or if multiple entries identify the target. Also hold if the identity of an earlier entry that could identify the target remains unresolved, including a same-number legacy entry with an unverified pointer. Reuse the unique verified entry for the target in Decisions-so-far, including a legacy entry.

  When reconciliation finds no entry for the target child, add one entry with the gist, a link to the resolved child, and a qualified marker with the owner and repository in lowercase. Append to the current body and write it back with `gh issue edit "${map:?}" --repo "github.com/${map_repo:?}" --body-file "$body_file"`, preserving every existing marker and pointer in the replacement body. Reconcile decision entries again on readback and at closeout. If the entire entry is gone and reconciliation finds no target entry or conflict, restore it from the existing resolution comment and latest map body, then verify again. Resume a partial run from the missing step after reconciling concurrent changes. A simultaneous stale-body write can still remove a verified entry.
