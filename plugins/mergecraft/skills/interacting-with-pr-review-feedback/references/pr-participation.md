# Pull-request participation

Decide whether a top-level pull-request comment, including a bot command, is
posted, and by whom. Mergecraft decides whether a contribution is worth posting;
Proseweaving owns register and prose mechanics;
`writing-github-issue-and-pr-markdown` owns the exact bytes; and the
[`coderabbit-top-level-comment` actuator](../../getting-prs-merged/scripts/post_coderabbit_comment.py)
posts them. This is a situational rule, not a per-comment permission prompt:
when standing and worth hold and the request carries the comment, post it.

## Standing

- A repository owner or maintainer, or an equivalent overriding authority, has
  settled standing.
- The pull request's author, or the author's agent, is a welcomed participant
  who ought to drive the pull request, while still weighing its standing with
  the repository's authorities and the worth of each contribution.
- A prior or assigned reviewer, an established contributor, and a participant
  who meets an explicit participation policy, or, absent one, whose
  contribution would reasonably be welcome, also have standing.
- When standing is uncertain, research it (roles, assignments, contribution
  history, participation policy) before asking anyone.
- When a participation rule excludes the actor, post nothing: explain the rule
  and offer a draft for a venue it allows.

## Worth

Post only a contribution that is confidently relevant, consequentially useful,
and new against the pull request's body and its whole discussion. Worth comes
from sharing key information, moving the pull request to its next needed
action, building consensus toward the parties' agreement, or another
effectual objective. Pull-request discussion is published procedural
documentation written in a discussion register: leave out filler, progress
chatter, repetition, verbose explanation, and belabored deliberation. A point
repeated in new words is still a repeat; materially changed evidence, such as a
new head, can make a repeat worth posting.

When the operator explicitly asks for a comment that repeats earlier discussion
or adds nothing new, name the earlier comment in one line and post only if the
operator still wants it.

## Bot commands

Body text never triggers a bot; only a posted command does. With standing and a
merge objective, asking a bot to review or approve the operator's own pull
request is ordinary participation the merge request carries, and a command the
operator asks for is carried by that request. A command whose effect reaches
beyond discussion needs that operation's own authority: merging, deploying,
changing protection, closing others' work, granting privileges, or changing code
through the bot. Leave such a command unposted and continue by the ordinary
route.

### CodeRabbit

Choose at most one command for the current head:

- `@coderabbitai review` when CodeRabbit is not reviewing the current head on
  its own (its check is skipped or absent, or it reports reviews paused) and no
  request exists for that head; or once, as the follow-up for its threads still
  open after its clean review of the current head, when its approval is not the
  last gate.
- `@coderabbitai approve` when its review of the current head found nothing
  actionable and its approval is the last gate you cannot clear. It resolves
  every CodeRabbit thread, and it approves only when the repository enables
  `reviews.request_changes_workflow`, which CodeRabbit reviews in `APPROVED` or
  `CHANGES_REQUESTED` state show. A later push can dismiss that approval, so
  recheck it on re-entry.
- No command while its review of the current head is running: its check is
  pending, or it acknowledged a request.

`resolve`, `autofix`, `fix-ci`, and `generate unit tests` are never follow-ups:
they act on every thread or change code instead of reviewing the current head.

## Before posting

Read the body, the whole discussion, and earlier requests. A first needed
request is worth posting; a duplicate, or one for a different head, is not. When
an earlier post may have gone through, find it by actor, pull request, head,
body, and time before any repost: credit it if it landed, and post only when
live state shows none.

## Posting

Compose the body under the
[GitHub Markdown authoring contract](github-markdown-authoring.md) and post it
once through the actuator. Bind the pull request, base, head, head repository
and owner, the expected authenticated login, the exact body bytes, and their
SHA-256. Independently verify the active login, then reread the comment's ID,
URL, pull request, head, author, body, and timestamp. A timeout leaves the
result unknown: reconcile it as above before any repost. The actuator edits no
PR text, feedback, CI, or merge state.

## Refusal

When a harness permission rule, classifier, or reviewer refuses the post
itself, report the refusal and ask the operator once, through the question tool
when the harness has one, with question and option text naming the comment and
the pull request, for example "Post `@coderabbitai approve` on PR 123". After
their answer names it, post once through the same actuator. A refused command
that only prepares the post, such as writing its body file, is not a refusal of
the post: prepare it another way, then post.
