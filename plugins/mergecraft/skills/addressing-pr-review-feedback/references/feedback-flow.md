# Feedback Flow

| Surface                                       | Owner                                                                  | Result                                                                                                                                                                                                                                |
| --------------------------------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Read threads, comments, review bodies, checks | acquisition script                                                     | complete head-bound live snapshot                                                                                                                                                                                                     |
| Snapshot/orientation mode                     | feedback coordinator                                                   | bound identities, acquisition completeness, live snapshot, and limitations; terminal before disposition or mutation                                                                                                                   |
| Freeze revision contract                      | feedback coordinator                                                   | exact source candidate identity, requirements or specification source or explicit absence, repository standards sources or explicit absence, owned paths, original mutation authority, and declared verification                      |
| Disposition                                   | `tricritical:adjudicate`                                               | one independence group plus the complete byte-identical frozen contract; exactly one of `accept`, `reject`, `already addressed`, `stale`, `duplicate`, `needs operator decision`, `blocked`, or `follow-up outside scope` per finding |
| Source revision                               | `tricritical:revise`                                                   | independently safe accepted findings plus the same complete byte-identical frozen contract                                                                                                                                            |
| Commit and push                               | `versionkeeping:checkpointing-and-publishing-git-work`                 | verified Git state                                                                                                                                                                                                                    |
| Changed PR facts                              | lifecycle caller                                                       | route to the selected content/publication owner                                                                                                                                                                                       |
| One semantic response                        | [response owner](../../interacting-with-pr-review-feedback/SKILL.md) | exact source correlation, writer bytes, selected Provingkit leaf receipt, and append-only semantic outcome |

Every frozen-contract field must be present. Treat pagination failure,
repository/PR ambiguity, a missing input, and changed base, head, or source
candidate identity as blockers; identity drift causes zero edits. An external
finding never expands the original mutation authority.

Partition feedback into independence groups before adjudication, and adjudicate
each group separately. A human decision blocks the group whose outcome it can
change. Complete every proven-independent, safe accepted group before returning
an unrelated operator decision. Never use independence to preempt a decision
that controls accepted work. External findings use Tricritical adjudication and
revision directly; this flow never creates a nested review loop.

Snapshot/orientation mode stops after complete acquisition. It does not freeze a
revision contract, assign dispositions, call Tricritical or Versionkeeping,
interact with feedback, publish, or mutate source, forge state, or refs.

Use the acquisition script's `--typed-epoch` mode for responses. Its default
orientation output cannot be admitted as response evidence.

The typed epoch carries one registry digest across pull requests, reviews,
conversation comments, inline comments, review threads, and their association
stubs. Deduplicate exact page-boundary repeats by typed identity. Reject a node
ID mapped to another kind or database ID, a same-kind database ID mapped to
another node, changed repeated evidence, contradictory thread scalars, or an
association that does not resolve. Record unavailable identity components
explicitly; review threads have a node ID but no database ID in the selected
public schema.

It also carries the Repository node ID and database ID, actual local
acquisition start and end observations, and complete pagination evidence for
each top-level collection and hydrated thread. The acquisition timestamps are
local observations, not provider timestamps. Required absence, contradiction,
or an unfinished page chain blocks the epoch without fabricated defaults.

Response acquisition retains every submitted nonempty typed source, including
resolved or outdated inline comments and reviewer replies. Body summaries are
for orientation. A review body and its inline comments receive independent
classification and adjudication; author, bot, and GitHub state do not assign a
disposition. Carry the classification result and evidence identity into the
response intent. Empty and pending review bodies remain metadata, and correlated
responses and control-only text do not automatically become new feedback.

Publishing a source fix ends the acquisition epoch. Reacquire against the new
head before composing a response. Source, thread, relevant comment-set, or head
drift ends an epoch before the next write. Carry forward only pending intents
proven independent and unchanged in source revision, head, authority, placement,
and exact response body. Preserve confirmed response evidence.

The response runtime resolves one permanent ordinary owner for the qualified PR
and exact typed source revision before it resolves a caller key. An unchanged,
independent intent carries forward under the same key. An intent invalidated
before `write_started`, or left with an interrupted validation, permanently
closes the old intent. Prepare a replacement before authoring its successor:
the runtime validates the entire bundle, acquires a complete epoch after the
terminal record, and durably publishes a read-only basis that binds the
terminal record digest, one exact successor source, its scope, and the
route-derived operation and placement. The coordinator then reclassifies,
re-adjudicates, reauthorizes, and reruns the writer against that basis. The
interaction owner accepts only the four exact canonical artifact wrappers in
replacement caller schema 2 and atomically consumes the latest unsuperseded
basis once. Ordinary, follow-up, retry, and carry-forward callers remain schema
1 and cannot express replacement. Any `write_started`, provider evidence,
stale or consumed basis, predecessor artifact bytes, incomplete proof, or
label-only assertion keeps the route closed.

The Response Outcome Bundle retains immutable write evidence and typed attempt
links, exclusive per-intent response identities, and typed post-write drift; it
is not a mutable review ledger or a replacement for acquisition.
Before any provider-capable action, fold and validate every retained record,
payload variant, identity reservation, and predecessor/successor reference.
Invalid semantic history blocks the complete action with zero provider calls.
Envelope version 2 does not grandfather an old semantic record: a baseless old
replacement, wrong-attempt reconciliation, conflicting reservation, or invalid
supersession or conversion fails closed without migration or repair.
Invoke the response owner once per independently authorized intent. Unknown
outcomes freeze dependent or conflicting work without claiming rollback of
completed responses. Reaction, thread resolution, and review submission remain
separate operations outside this response flow.

Before each invocation, load and record the reviewed revision of the response
procedure, preserve the exact intent's original key, and supply its complete
head-bound binding. Consume one closed response-identity decision from the
interaction owner rather than reconstructing unknown competitors or identity
roles from outcome maps. Equal provider-observable correlation blocks that
group without collection attribution; a separately unequal group continues
only after its own independence evidence and full revalidation.
