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

Run source checks and synthetic cases through the maintained test schedule;
retain the candidate revision and actual results. Procedure discovery and
caller application need their own consumer checks. None of these checks proves
effective Daybreak execution, current app behavior, installation, signal-safe
shutdown, or live recovery. The general matching-reply observer and finite Claude consuming-control lookup
remain separate source work. Advertise it only after implementation and checks at its
actual boundary.
