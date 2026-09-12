---
name: interacting-with-pr-review-feedback
description: Use when composing and posting one authorized response to an exact pull request review comment, conversation comment, or submitted-review body, or reconciling that response's uncertain result.
---

# Interacting With PR Review Feedback

Own one semantic feedback response: its authority, wording, placement, exact
source correlation, portable writer invocation, and dispatch to one Provingkit
leaf actuator. Perform exactly one authorized response intent per invocation.

1. Read [the interaction contract](references/interaction-authority.md). Take a
   complete, freshly acquired source epoch and the exact source's adjudication
   and response authority from the feedback coordinator. A summary or permalink
   alone cannot identify the typed source. Require the epoch-wide typed identity
   registry and its digest, Repository node and database IDs, the actual local
   acquisition start/end observations, and complete top-level and hydrated-
   thread pagination evidence. Local acquisition observations are not provider
   timestamps. Unavailable provider identity components must be explicit.
   Missing, contradictory, or incomplete evidence blocks admission.
2. Select `feedback-inline-response` or `feedback-conversation-response` from
   the source kind. An inline comment receives a reply
   in its existing thread, including when the source is itself a reply or the
   thread is outdated or resolved. A PR conversation comment or submitted-review
   body receives a new top-level PR conversation comment. Keep a review body and
   its inline comments separate; a duplicate disposition may require no response.
3. Compose the response using the selected Mergecraft review-voice and Tidesmith
   writing policy before fixing its bytes. Record the selected policy sources
   and any unavailable route. Where the selected register policy is unavailable,
   the client's ambient writing instructions govern; do not claim that missing
   policy was loaded or evaluated. Policy shapes wording and never selects the
   operation or grants authority. State the evidence naturally, without a
   formulaic acknowledgement. Every top-level response includes a natural,
   human-visible permalink to its exact source, such as “I applied
   [your suggestion](https://github.com/OWNER/REPO/pull/123#issuecomment-456).”
4. Invoke the `github-markdown-content` portable writer operation through the generated
   [GitHub Markdown authoring contract](references/github-markdown-authoring.md)
   for the selected reply or PR conversation field. Compose compatible consumer
   instructions and stop on a material conflict. Freeze its exact UTF-8 body,
   including line endings and terminal-newline state, and its writer identity.
   Give those bytes opaquely to the selected actuator. Never inject a marker,
   reflow the body, change it after admission, or edit the created response.
5. Resolve the permanent ordinary owner from the stable typed Repository and
   pull-request identities, PR number, source kind and typed identity, and exact
   source revision before resolving the caller's immutable intent key. Compare
   those canonical typed values, not only their SHA-256 indexes. Repository
   name and owner, PR permalink, head/base, head repository, source permalink,
   and placement remain exact epoch and binding evidence; a rename or transfer
   cannot create another owner, while any stale full binding still blocks a
   write. Bind the
   key once to the owner, PR/head, operation and placement, authority and
   classification, adjudication, and exact writer/body identity. Ordinary and
   follow-up admissions are atomic. Validate every record and semantic
   reference in the complete bundle before admission or any provider-capable
   action. Then commit `prewrite_validation_started` before the validation read
   and revalidate the complete binding immediately before a write.
   If the source, thread, relevant comment set, or head changed, end the epoch
   and commit terminal pre-write invalidation. A read interruption after the
   validation start is also terminal for that old intent. Neither can later be
   revived by provider state reverting.
   For either terminal state, run `scripts/response_cli.py
   prepare-replacement --state-dir STATE --intent-key KEY --repo OWNER/REPO`
   with the old key before requesting new semantic work.
   The runtime validates the whole history, acquires a complete post-terminal
   epoch, and publishes a read-only replacement basis without writing a
   response. When a repository rename or transfer makes the predecessor's old
   locator stop resolving to the same typed Repository and pull request, stop
   before semantic authoring and require current-locator resolution by the
   acquisition owner. Once fresh full context resolves to the same stable typed
   source revision, the basis and successor reuse its permanent owner. Reclassify,
   re-adjudicate, reauthorize, and rerun the writer only
   against that basis. Invoke the successor with closed caller schema 2: a
   fresh key, `intent_kind: ordinary`, the basis ID, and exact canonical-byte
   wrappers for classification, adjudication, authority, and writer result.
   The runtime derives source and route from the basis, requires the separate
   body bytes to equal the writer result, and consumes the latest unsuperseded
   basis once.
6. Use `scripts/response_cli.py invoke` with the durable state directory, bound
   intent JSON, and exact body file, following the contract's runtime interface.
   Require a committed `write_started` record before the selected Provingkit
   response actuator can run. Consume its authoritative request, result, full
   created/requested/reread identity evidence, and exact-reread receipt. Preserve
   thread state. Atomically publish the complete provider resolution, semantic
   outcome, drift, and all identity observations or claims; do not leave a
   separately joinable success record and do not replace earlier evidence.
7. Complete on `confirmed_success` or exact-replay `confirmed_no_op`. Retry a
   retryable `confirmed_failure` only when evidence proves no write and the
   unchanged intent passes full revalidation. Never automatically retry
   `unknown`: use `scripts/response_cli.py reconcile` with the same key. Reread
   its retained typed response identity when available. Otherwise acquire the
   complete response collection and exclude nonexclusive candidates. Before
   rereading a selected candidate, durably reserve its full typed identity for
   the current effective unknown attempt. Explicit supersession transfers the
   same reservation or closes a different one into permanent same-intent
   observation. Success converts it to ownership; `still_unknown` converts it
   to observation. Credit
   only one stable, exclusive, exact result. Empty, ambiguous, or incomplete
   observations stay unknown and permit no write. Keep reconciliation
   `absence_evidence` null; authored absence assertions grant no retry
   capability. Treat post-write drift as `observed`, `not_observed`, or
   `unknown`; later matching state cannot make historical `unknown` clean.
   The semantic fold's private response-identity authority supplies one closed
   reconciliation decision before any collection read: already confirmed,
   ineligible, known typed identity, ambiguous effective-unknown group, or
   collection discovery. Treat the full canonical correlation value as equal,
   not its SHA-256 alone. It contains the stable typed repository and PR target,
   operation and response object kind, full placement, actor login, and all
   exact body-wrapper fields. Head, base, repository names, head repository,
   and permalinks remain mandatory full-binding checks but cannot distinguish a
   possible provider result. If two current effective unknown attempts have the
   same value, retain both original keys and record `still_unknown` without
   listing, attributing, reserving, rereading, or writing. This blocks only that
   group; a different group continues only with its own independence evidence
   and complete revalidation.

A fresh key, changed body, or operator assertion cannot bypass an unknown
result. An explicitly authorized correction or addendum uses a new intent linked
to a confirmed predecessor outcome; it is a follow-up, never a retry or edit.
An intent invalidated before any `write_started`, or left with an unmatched
validation start, may use the two-phase replacement route above. Caller
timestamps, renamed evidence IDs, predecessor artifact bytes, and free-form
drift labels do not establish freshness. Any `write_started`, leaf evidence,
incomplete proof, or operator assertion closes that path. Old version-2
replacement records with no preceding runtime basis, wrong-attempt
reconciliation, and conflicting reservation histories invalidate the complete
bundle before provider access; preserve their bytes without repair or migration.
If semantic persistence fails after GitHub confirms a write, retain the leaf
evidence and reconcile before any further write for that intent. Credit an
exactly verified response even when post-write drift ends the epoch; report the
drift without claiming that all feedback is addressed.

## Completion and handoff

End every executed, proposed, or blocked invocation with one compact `Intent
handoff` block. Emit a separate block for each intent; never collapse two
intents into shared fields. Keep these operational fields outside the authored
GitHub comment. Report observed evidence, and label anything absent or not run
as a future gate rather than inventing it.

Each `Intent handoff` accounts for:

- **Intent:** executed, proposed, or blocked state and the immutable caller key.
  If no key has been supplied because admission has not occurred, say
  `absent—not yet admitted`. Include the permanent source-revision owner and any
  linked retry, reconciliation, follow-up, or never-executed replacement.
- **Binding:** exact typed source identity and revision, repository-qualified
  PR/head, selected operation/placement, acquisition registry digest, and the
  frozen dependency inputs used by this intent. A dependency change makes the
  handoff stale.
- **Decision and policy:** authority and adjudication evidence or the missing
  gate; selected writing-policy sources, any unavailable route, and the
  limitation that policy shapes wording without granting authority or choosing
  the operation.
- **Pre-write revalidation:** this intent's own immediate pre-write check and
  result, the committed `write_started` identity when present, and whether the
  provider boundary could have been crossed. If no write was attempted, say
  `not run` and require fresh per-intent revalidation immediately before any
  future write.
- **Writer bytes:** writer identity, exact UTF-8 body binding including line
  endings and terminal-newline state, and whether those bytes were forwarded
  unchanged. Mark any not-yet-frozen binding as absent.
- **Evidence chain:** attempt identity and authoritative result; stable typed
  created, requested, and reread response identities and their equality;
  per-intent durable leaf-receipt identity or digest; then append-only semantic
  outcome identity and typed attempt, retry, reconciliation, follow-up, or
  replacement links, with earlier evidence preserved. For a
  proposed or blocked invocation, mark each unavailable stage separately and
  name it as required before that intent can complete.
- **Replacement basis:** for a never-executed replacement, report the terminal
  predecessor record and digest, basis and successor-epoch identities,
  supersession or consumption state, and the four exact artifact digests.
  Distinguish runtime-recorded acquisition from locally authored semantic
  decisions; neither is production or provider-write authority by itself.
- **Status:** terminal state; reconciliation result or requirement; post-write
  drift assessment as `observed`, `not_observed`, or `unknown`; dependent or conflicting work blocked and any proven-independent work
  that may continue; and remaining feedback scope. For `unknown`, retain the
  same key and distinguish a unique exact result from empty, ambiguous, or
  incomplete observations that remain unknown. Credit completed outcomes
  without implying that all feedback is addressed; there is no batch atomicity
  or rollback.
- **Procedure revision:** the reviewed source revision containing this skill,
  `interaction-authority.md`, the response runtime/store, stable source-owner
  helper, response-identity helper, and
  its current behavior evidence. Record the closed runtime decision consumed.
  A source or evidence dependency change makes this procedure record stale.

This response capability performs no reaction, thread resolution or reopening,
review creation or submission, approval, request-changes submission, review edit
or dismissal, bot-review request, source edit, PR publication, ready transition,
merge, or Issue lifecycle operation. GitHub's shared IssueComment endpoint is
plumbing for a verified PR target; it exposes no generic Issue-comment operation.
