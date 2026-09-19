# GitHub Development Relations and Automatic Issue Closure

GitHub can record multiple Issue–PR Development links and now exposes public
GraphQL operations to add and remove manual links. Those links are closing
references: the supported inputs do not distinguish contribution from
completion. The documented way to suppress closure is a repository setting,
not a per-link mode. Adding historical links to already merged PRs remains an
unqualified operation because the primary sources do not specify its immediate
effect on issue state.

## Research Contract and Evidence

This answers [Research GitHub Development link and automatic closure semantics](https://github.com/nisavid/provingkit/issues/86)
as of 2026-09-17. It establishes available surfaces and evidence limits; it does
not select policy, change repository settings, or qualify a mutation through a
live experiment. No test Issues or PRs were created and no existing ones were
edited. The reusable result is this note; downstream design and implementation
should load its supported-surface and unresolved-behavior sections before
choosing an actuator or interpreting a link as completion.

Evidence labels below mean:

- **Documented:** current GitHub documentation or an identified product-team
  statement specifies the behavior.
- **Live schema/read:** authenticated, read-only GitHub.com introspection or
  queries accepted the named fields on this date. This proves their exposure,
  not mutation behavior or permissions.
- **Inference:** a conclusion drawn from the documented model, identified as
  such where consequential.
- **Unverified:** a behavior requiring a controlled test or additional
  authoritative documentation.

Context7 resolved GitHub's official documentation and supplied two focused
documentation queries. The underlying sources were then read directly through
GitHub's API. The evidence baseline is
[`github/docs` at `72f69c8`](https://github.com/github/docs/tree/72f69c8a8f9d5bc3b6028895b11ff9750b85f5dc)
and the
[GitHub.com REST OpenAPI description at `d4278c8`](https://github.com/github/rest-api-description/blob/d4278c869e367f5d6d4e0f46878119128abba77b/descriptions/api.github.com/api.github.com.json).
Live GraphQL introspection was compared with the
[published Issues schema source](https://github.com/github/docs/blob/72f69c8a8f9d5bc3b6028895b11ff9750b85f5dc/src/graphql/data/fpt/schema-issues.json).
CLI observations used `gh` 2.97.0 and its local help.

## What Each Kind of Reference Means

| Surface | Native Development relation | Closure and removal |
| --- | --- | --- |
| Manual Development link | Yes; the public mutation calls it a manually linked closing reference | Default behavior closes the issue when the linked PR merges into the default branch. Remove through the manual-link control or `removeCloseIssueReferences`. |
| Closing keyword in PR description | Yes, when the PR targets its repository's default branch | Keywords express closing intent. Remove the keyword from the description; manual unlink does not remove this source. |
| Closing keyword in a commit message | Does not make the containing PR appear as a linked PR | The documented trigger is the commit reaching the default branch. Repository-setting interaction is not separately specified. |
| Ordinary issue reference in text | A rendered link and normally a backlink; not sufficient evidence of a Development closing relation | No supported closing keyword is present. A reference such as `Refs #12` must not be treated as `Closes #12`. |

These distinctions follow the [linking guide][linking],
[autolink documentation][autolinks], and
[manual-reference mutation contracts][graphql-issues]. Ordinary references can
produce timeline events; seeing a PR in a timeline is not the same observation
as finding it in the current closing-reference connection.

The recognized keyword families are `close`/`closes`/`closed`,
`fix`/`fixes`/`fixed`, and `resolve`/`resolves`/`resolved`. The supported place
for a PR's closing declaration is its description, not an arbitrary comment.
Use `Closes #12` within one repository and `Closes OWNER/REPO#12` across
repositories; repeat the full syntax for multiple issues. Case and an optional
colon do not remove closing intent. [Source: linking guide][linking].

The native relation does not carry a documented contribution/completion role,
supersedes role, or per-edge non-closing flag. This is a **supported-surface
finding**, not a claim that GitHub has no internal representation of those
concepts. The inspected mutation inputs contain only the issue ID, PR IDs, and
an optional client mutation ID. The returned `IssueEdge` contains a cursor and
node, not editable relationship metadata. [Source: public schema][graphql-issues].

## Cardinality, Repository Boundary, and PR State

| Question | Established result |
| --- | --- |
| One PR to several issues | The UI documentation permits up to **10 manually linked issues per PR**. This is not a documented cap on closing-keyword references. |
| One issue to several PRs | Supported: issue reads return a PR connection, and the add mutation accepts multiple PR IDs. No total per-issue PR limit was found in the inspected primary sources. Do not invent one. |
| Mutation batch size | Both add and remove accept at most **10 PR IDs per request**. This differs from the UI's 10-issues-per-PR limit. The docs do not establish that batch size as a total relation limit. |
| PR-side manual UI | Requires repository write permission; issue and PR must be in the same repository. |
| Issue-side manual UI | Requires repository write permission; supports choosing another repository containing the PR or branch. The docs do not spell out the full cross-repository permission matrix. |
| Same/cross-repository keywords | Both are documented, using the syntax above. |
| Non-default PR base | Description keywords are ignored: no keyword-derived link is created, and merging that PR does not close the issue through those keywords. |
| Default PR base | The documented ordinary closure trigger is merge into the default branch. A single qualifying linked merge can close the issue; the relation is not an “all linked PRs merged” completion gate. |
| Draft/open PRs | The schema exposes PR state and `isDraft`, but the manual-link docs do not state a draft-specific eligibility or permission contract. No draft-link mutation was tested. |
| Merged/closed-unmerged PRs | Historical reads are supported through `includeClosedPrs: true`. The docs do not establish whether every such PR is selectable or mutable through every UI/API route. Adding links after merge was not tested. |

Sources: [linking guide][linking] and [public GraphQL Issues reference][graphql-issues].
For the single-merge consequence, GitHub's documented trigger names a linked
PR's merge; the product team's repository-setting proposal explicitly made it
an all-or-none repository policy rather than an aggregate completion rule.
[Product-team proposal][setting-proposal].

The manual-link guide does not restrict manual association to default-base
PRs, but it does restrict automatic closure to the default-branch merge.
Treating that distinction as guaranteed eligibility for every non-default-base
state would exceed the documentation. Retargeting and later default-branch
integration need qualification if they become supported workflow inputs.

## The Repository Auto-Close Setting

The exact checkbox is **Auto-close issues with merged linked pull requests**, at
**Repository settings → General → Issues**. Repository administrators and
maintainers can configure it. It is enabled by default. Disabling it overrides
the default closure behavior when linked PRs merge.
[Configuration documentation][auto-close] and [release announcement][announcement].

| Interaction | Evidence boundary |
| --- | --- |
| Manual links | Within the documented linked-PR scope of the setting. Disabling automatic closure does not introduce a new per-link type. |
| Explicit description keywords | GitHub documents one linked-PR setting and no keyword override. The product-team proposal describes all-or-none repository behavior and separates a new non-closing keyword into a different proposal. Therefore, preserving an explicit-keyword override while disabling the checkbox is **not a supported promise**. The precise runtime interaction was not independently tested here. |
| Commit-message keywords | The commit-closing path is documented separately and does not create the containing PR's Development link. The setting docs do not explicitly settle direct pushes, squash messages, rebases, or other commit-delivery paths. **Unverified.** |
| Cross-repository links | The setting is presented as controlling issues in the configured repository, suggesting the issue repository owns the policy. Exact precedence when issue and PR repositories have different settings is **unverified**. |
| Enumerating links while closure is disabled | Neither the setting docs nor the connection descriptions explicitly guarantee which manual links `closingIssuesReferences` and `closedByPullRequestsReferences` return with the checkbox disabled. **Unverified.** Association visibility in the UI does not by itself qualify an API inventory. |
| Changing the checkbox after a PR has merged | Retroactive closure, reopening, and reevaluation are not documented. **Unverified.** |
| Adding a link to an already merged PR | Neither the checkbox docs nor add-mutation contract specifies whether the add immediately closes an open issue or only records an association. **Unverified; historical repair cannot assume a state-neutral write.** |

The [product-team proposal][setting-proposal] and
[implementation selection][setting-selection] identify the repository-wide
option as the implemented direction. Reports from ordinary users in the
announcement discussion are not promoted here into runtime guarantees.

**Available control:** the documented repository Settings UI. I found no
supported public setting field in the inspected REST repository GET/PATCH
schemas, live GraphQL `Repository`/`UpdateRepositoryInput`, or `gh repo edit`
flags. This negative finding is bounded to those inspected public surfaces;
an internal browser endpoint is not a public API contract.
[REST schema][rest-schema], [GraphQL repository reference][graphql-repositories],
and [`gh repo edit` manual][gh-repo-edit].

## Supported Reads and Writes

### Read the Current Relation, Then Its History

Use `PullRequest.closingIssuesReferences` in the PR-to-issue direction and
`Issue.closedByPullRequestsReferences` in the issue-to-PR direction. Both are
paginated connections with `first`/`after`, `last`/`before`, `totalCount`, and
`pageInfo`. Both accept `userLinkedOnly: true` for manual relations or
`excludeUserLinked: true` to exclude manual relations. Query these views
separately; do not assume they form disjoint sets when a pair has multiple
sources. [Issue reference][graphql-issues] and [PR reference][graphql-pulls].

For historical inspection, explicitly pass `includeClosedPrs: true` on the
issue-side connection. Its general description still says open PRs; the
argument is the documented opt-in for closed results. Preserve `state`,
`isDraft`, `mergedAt`, repository identity, and IDs rather than collapsing
merged and closed-unmerged into one status. A read-only query against an
existing issue and a merged PR accepted the connections and manual/detected
filters on 2026-09-17; those queried connections were empty, so this validates
field availability rather than nonempty historical classification.
[Issue reference][graphql-issues] and [PR reference][graphql-pulls].

One connection can be paginated with this query shape:

```graphql
query($owner: String!, $name: String!, $number: Int!, $endCursor: String) {
  repository(owner: $owner, name: $name) {
    issue(number: $number) {
      id
      closedByPullRequestsReferences(
        first: 100, after: $endCursor, includeClosedPrs: true
      ) {
        totalCount
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          number
          url
          state
          isDraft
          mergedAt
          baseRefName
          repository { nameWithOwner }
        }
      }
    }
  }
}
```

`gh api graphql --paginate` supports this `$endCursor`/`pageInfo` contract.
Paginate every repository collection and each nested relation separately;
one exhausted outer page does not establish complete nested history.
[`gh api` manual][gh-api].

`timelineItems` supplies `ConnectedEvent`, `DisconnectedEvent`, and
`CrossReferencedEvent`. The last exposes `willCloseTarget`, but that is a
read-only event property, not a non-closing link actuator or a guarantee for
every future setting change. Timeline history complements current relations;
it does not replace them. REST also supports paginated
`GET /repos/{owner}/{repo}/issues/{issue_number}/timeline` with `per_page` up to
100. [GraphQL reference][graphql-issues] and [REST timeline reference][timeline].

### Mutate Through the Named Public Operation

| Desired effect | Supported surface and boundary |
| --- | --- |
| Add manual native links | GraphQL `addCloseIssueReferences(input: AddCloseIssueReferencesInput!)`. Required `issueId: ID!` and `pullRequestIds: [ID!]!`; optional `clientMutationId: String`; at most 10 PR IDs. Target must be an Issue. |
| Remove manual native links | GraphQL `removeCloseIssueReferences` with the corresponding input shape and batch limit. Explicitly leaves keyword-detected references unchanged. |
| Change closing keywords | Edit the PR description through the UI, REST PR update, GraphQL `updatePullRequest`, or `gh pr edit --body-file`. This is a body mutation and must preserve unrelated authored content. |
| Change repository auto-close policy | Documented Settings UI; no supported public API or dedicated CLI flag found in this research. |
| Record ordinary contribution/reference text | Normal body/comment authoring surfaces create references, not a typed neutral Development edge. The difference must remain visible to the consumer. |

Sources: [GraphQL Issues reference][graphql-issues],
[REST PR update documentation][update-pr], and [`gh pr edit` manual][gh-pr-edit].
Live schema inspection found both manual-link mutations and did **not** find a
mutation named `linkPullRequestToIssue` or `unlinkPullRequestFromIssue`.
The inspected REST description has no equivalent manual closing-reference
route. `gh api graphql` can carry the supported mutations; the inspected
`gh pr edit` flags have no dedicated manual-link flag.

**Permissions:** manual UI linking requires write access, while the checkbox
requires administrator or maintainer access. Public mutation schemas do not
specify the precise minimal fine-grained token permissions, actor permissions
on both repositories, or error/partial-success behavior for each historical
state. No mutation was executed to determine these. Private reads also depend
on the caller's access; a missing inaccessible item is not proof of absence.
Do not interpret schema exposure or a successful read as mutation authority.
[Linking guide][linking], [setting guide][auto-close], and
[mutation contracts][graphql-issues].

## Historical Repair and Remaining Qualification

Removing a manual link and removing a keyword are different operations. A
pair can require both if both sources are present; reread current connections
after the intended source change. No inspected source promises that unlinking
reopens an issue or reverses historical closure. Likewise, there is no native
supersession role in the inspected relation: keeping or replacing an old PR's
association is a domain decision, not an API-supplied completion verdict.
[Linking guide][linking] and [remove-mutation contract][graphql-issues].

The following are the concrete unknowns that can change a later execution
contract. They require a separately authorized, isolated qualification
exercise or authoritative clarification; no such experiment was performed.

1. **Historical add:** link an already merged PR to an open issue, with the
   checkbox enabled and disabled. Observe relation membership, issue state,
   and timeline before and after. Include cross-repository cases if supported.
2. **Closure paths:** separate manual links, description keywords, commit
   keywords delivered by a PR, and commits delivered directly to the default
   branch. Confirm whether explicit keywords ever override a disabled checkbox.
3. **Repository ownership:** vary the issue and PR repositories' settings
   independently and verify which controls cross-repository closure.
4. **State/base eligibility:** cover draft/open, merged, and closed-unmerged
   PRs, default/non-default bases, retargeting, and later integration into the
   default branch. Test UI and public mutation behavior only for the inputs
   the implementation will claim to support.
5. **Permissions and mutation results:** establish least required access,
   duplicate-add behavior, batch failure semantics, cardinality enforcement,
   dual manual/keyword provenance, and what a verification reread must prove.
6. **Reads with closure disabled:** verify that both closing-reference
   connections retain manual Development links, including merged and
   closed-unmerged PRs with `includeClosedPrs: true`. The public API cannot
   currently supply the checkbox state; a cached setting observation has no
   documented freshness guarantee and cannot silently replace a live policy
   precondition.

The decision supported now is the boundary itself: the public API can maintain
native closing-reference associations; it cannot encode a per-edge distinction
between contribution and completion. Repository-wide suppression is documented,
but a history-wide repair still lacks evidence that post-merge linking is
state-neutral. Choosing a policy or authorizing qualification belongs to the
downstream decision, not this research result.

[linking]: https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue
[autolinks]: https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/autolinked-references-and-urls
[auto-close]: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/managing-auto-closing-issues
[announcement]: https://github.blog/changelog/2025-04-23-users-can-now-choose-whether-merging-linked-pull-requests-automatically-closes-the-issue/
[setting-proposal]: https://github.com/community/community/discussions/17308#discussioncomment-12504704
[setting-selection]: https://github.com/community/community/discussions/17308#discussioncomment-12543144
[graphql-issues]: https://docs.github.com/en/graphql/reference/issues
[graphql-pulls]: https://docs.github.com/en/graphql/reference/pulls
[graphql-repositories]: https://docs.github.com/en/graphql/reference/repos
[rest-schema]: https://github.com/github/rest-api-description/blob/d4278c869e367f5d6d4e0f46878119128abba77b/descriptions/api.github.com/api.github.com.json
[timeline]: https://docs.github.com/en/rest/issues/timeline#list-timeline-events-for-an-issue
[update-pr]: https://docs.github.com/en/rest/pulls/pulls#update-a-pull-request
[gh-api]: https://cli.github.com/manual/gh_api
[gh-pr-edit]: https://cli.github.com/manual/gh_pr_edit
[gh-repo-edit]: https://cli.github.com/manual/gh_repo_edit
