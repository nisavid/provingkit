# Develop Surreal Intercom

Surreal Intercom owns communication mechanics and their maintained procedure.
Rolecasting owns delegation selection, authority interpretation, and supervision.

The extraction input is communication revision
`699365c7245edd249e3c6fd36c9479d9e5843351`. Runtime modules remain together under
`skills/communicating-with-agents/scripts/`; imports and installed links resolve
inside this plugin. Runtime stores and captures stay outside installed resources.

The owning source validator is `scripts/validate_surreal_intercom.py`. Its
documented `--write-content-lock` route writes
`release/plugin-content-locks/surreal-intercom.json`; run the ordinary validator
after regeneration. Run the command suites under
`tests/plugins/surreal_intercom/`, package validator tests, affected Rolecasting
checks, source-disposition checks, and the artifact projector's standalone
Agent Plugins and Claude cases. Evaluations belong under `evals/surreal-intercom/`.
Use the repository's maintained source-test schedule for final Kit checks.

The content lock binds plugin-relative source files and the external evaluation
files in a separate repository-relative `evaluations` section. The writer freezes
source and destination identities before validation and refuses observed drift
through the existing replacement transaction. It preserves the previous lock
on a failed source check and preserves a concurrent destination edit.

The [coordination register](https://github.com/nisavid/provingkit/tree/main/docs/coordination)
retains source and operating evidence. Catalog revision
`85f22c6d7fc93e52189219144f8245b70fe97750` and
[Daybreak research](https://github.com/nisavid/provingkit/blob/d94a859056129fa895685d9b0cd2c767e534d94d/docs/superpowers/research/2026-11-05-daybreak-invocation-surfaces.md)
are separate integration inputs. Keep historical claims and private records in
place; a path move supplies no new live qualification.

The [Codex Daybreak recipient procedure](skills/communicating-with-agents/references/codex-daybreak-recipient.md)
owns invocation of `codex_daybreak_sender.py`: caller-owned native creation and
reads, retained bootstrap evidence, claimed owner submission, task observation,
and explicit continuation on the same child. Keep its caller-control shapes and
retained input/status contracts aligned with the script. The helper is not a
native creation/read actuator or a general reply observer.

Synthetic coverage for this procedure must distinguish preparation, direct and
pending creation binding, completed/pending/unknown bootstrap, setup receipt and
saved-selection readback before task submission, accepted versus uncertain
submission, bounded caller-owned task observations, and fresh continuations.
Check conflicting and repeated intake, interruption barriers, missing or stale
references, remote-child refusal before an observation call, and unchanged
original attempts after uncertainty. Keep the Daybreak outgoing-frame limit at the shared framing
write checks, including protocol-generated responses, and require refusal before
the oversized frame reaches the peer. Ordinary existing transport profiles retain
their current limits.

The [Codex Worker observation diagnostic](skills/communicating-with-agents/references/codex-worker-observation-diagnostic.md)
owns the source-only, one-shot `codex_worker_observer.py` contract. Its CLI tests
must use test-owned Unix peers and files, exercise the actual command, prove the
read-only traffic allowlist and finite aggregate limits, and distinguish useful
selected views from binding, freshness, history, finalization, and closure
unknowns. Shared transport and snapshot changes retain the busy sender,
reconciler, and idle sender suites as regression gates. Native acquisition,
installation, recurring supervision, and recovery activation remain separate.

Run source checks and synthetic cases through the maintained test schedule;
retain the candidate revision and actual results. Procedure discovery and
caller application need their own consumer checks. None of these checks proves
effective Daybreak execution, current app behavior, installation, signal-safe
shutdown, or live recovery. The general matching-reply observer and finite Claude consuming-control lookup
remain separate source work. Advertise it only after implementation and checks at its
actual boundary.

The [Codex route nomination procedure](skills/communicating-with-agents/references/codex-route-nomination.md)
owns bounded direct-primary listener classification and private nomination
publication. Its public CLI fixture must keep unrelated held listeners in the
sample while distinguishing a single canonical primary pathname from zero or
several. Multiple rows with one name require one stable backing socket on a
supported filesystem. Cover missing or multiple matches and a changed socket
cookie or mount namespace through the public producer fixture. Shortened and
legacy routes remain unsupported. These
synthetic checks establish no installed route or live peer qualification.
Run exactly two complete classifications, each within the original descriptor,
link-byte, Unix-row, and Unix-byte limits, under one shared watchdog. Their
aggregate work is capped at twice the per-classification limits; the closed
record reports per-classification high-water counts. Require the same selected
listener and descriptor/socket identity. For rows that share one pathname,
require the same complete candidate set and backing evidence in both
classifications. Cover original maximum-range
success on both passes, the retained 694-descriptor/2,401-row sample, a final-only
second canonical listener, lost listening eligibility, an unrelated native-pipe
change, and every final-pass bound. This is not an atomic or perpetual-stability
claim.
Exercise list, `null`, string, and number request roots through the real public
CLI and require the stable no-publication/no-connection refusal before any
production observation.

Requested-reply coverage uses source-owned procedure examples, the ordinary
mailbox and peer serializer, and both detached projections. Exercise native and
nomination-backed readiness across all three reply/wait cases. Verified bound
native reach uses no nomination and no `reply_route`. For nomination-backed
readiness, a Claude origin constructs `claude-mcp` from its safe Claude result,
and a Codex origin constructs `codex-owner-admission` from its safe Codex result
and corroborated invocation. Pass both through actual planning and serialization;
keep no-reply messages byte-identical without `reply_route`. Reject identity or
correlation mismatch, malformed nomination specifications, unknown route kinds,
and raw endpoint fields before planning. Send a reply back through each route
kind with the route taken unchanged from the received envelope, and require the
original sender as destination and the original exchange correlation. These
cases establish source addressability, not current installation, permission,
delivery, or reply handling.

By-name Claude sends use a disposable stdio child that serves a catalog with
`SendMessage` and `ListAgents` and a synthetic listing in the one observed
Claude Desktop layout the
[Claude MCP sender](skills/communicating-with-agents/references/claude-mcp-sender.md)
documents. Cover exactly one `ListAgents` call and one `SendMessage` call,
with the send reply retained as `unknown`. Check that every invalid listing refuses before
`SendMessage`, including unsupported rows beside a valid destination,
embedded control text, pagination, caller identity conflicts, and a peer total
that differs from its row count. Exercise no matching row, ambiguous name,
ambiguous selection, and a selected reference absent from the listing.
Check that a matching singleton selection sends the bare name and that
selection qualifies an address when several rows carry the name. Cover the
300-UTF-16-unit name and the 4,096-byte bare frame that grows to 4,105 bytes
with a reference. Check unrelated unreadable titles, the exact skipped-row
counts in results and durable records, and refusal when an unreadable label
could carry the requested name.
Check every parsed field of the example rows and restore the initialized
mailbox before each listing mutation. Show that the sender and `prepare` refuse
a name the profile cannot address before any claim. Show that a planned
recipient whose `thread_id` is not the
requested name is refused by the sender and by `prepare` before any listing,
and that a reply through an unchanged route of either kind still reaches the
original sender when the outbound message went by name. Show that a refusal
before possible submission records `not_delivered` on both paths, including the
frame-size refusal, that an ambiguous name's refusal lists only the rows that
carry the name, and that a later attempt with the selection and both
`after_attempt` and `decision_ref` writes one send call and the mailbox keeps
its reconciliation. Show that one of those fields without the other is refused before
any claim, in the sender and in `prepare`, and that an attempt that recorded
possible submission is not followed by another. Show that a
supplied route is sent by that route with no listing, and that a refused name
request tries no second path. Cover the close: a child that exits on closed
input takes no signal, one that outlives it is terminated rather than killed,
one that writes while it stops is drained within the quotas, and a descendant
that holds the pipes does not extend the close. On overflow, confirm the first
error is retained and the other pipe keeps draining. Keep the listing profile and
its synthetic fixtures tied to the observed layout. The duration units come
from the Claude Code 2.1.331 formatter.
