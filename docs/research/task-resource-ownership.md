# Task resource ownership

Record who must account for a task's resources independently of its native
attachments. Versionkeeping's [cleanup procedure](../../plugins/versionkeeping/skills/checkpointing-and-publishing-git-work/references/terminal-cleanup.md)
defines ownership, resource disposition, and the separation between task
archival and resource removal. This document assesses automation for that rule;
it does not establish a shipped hook or bookkeeping service.

## Verified control surfaces

The Codex desktop tools exposed to this task have these contracts:

- `set_thread_archived` can archive the calling task with `threadId` omitted.
  It does not require a worktree attachment or completed resource removal.
- `create_worktree` creates and attaches a managed worktree, while leaving the
  task in its existing checkout. Worktree creation, attachment, task working
  directory, and command working directory are separate facts.
- `attach_artifact` and `remove_artifact` support pull requests only. There is
  no exposed control to attach an existing worktree or change this task's
  working directory. `handoff_thread` moves another task, not its caller.
- `archive_worktree` requires the attachment identity returned by
  `list_artifacts`. It preserves a Git snapshot, excludes ignored files, and
  rejects primary, pinned, shared, initialized-submodule, and embedded-repository
  worktrees. Missing registration can therefore prevent this actuator without
  changing resource ownership or preventing task archival.

These are available-tool contracts, not an end-to-end test of every native
operation. The observed attachment omission does not identify its upstream
cause or establish a failure rate.

The installed Codex CLI reported `0.159.0`. Its public
[hook schema](https://github.com/openai/codex/blob/rust-v0.159.0/codex-rs/hooks/src/schema.rs)
provides session identity, transcript location, working directory, and
tool-event inputs that can support an observer. Its
[SessionEnd implementation](https://github.com/openai/codex/blob/rust-v0.159.0/codex-rs/hooks/src/events/session_end.rs)
runs at session teardown, with reason `other` and a three-second maximum;
this event does not establish task archival or resource disposal eligibility.
The public
[`turn/start` parameters](https://github.com/openai/codex/blob/rust-v0.159.0/codex-rs/app-server-protocol/schema/json/v2/TurnStartParams.json)
permit a working-directory override through the owning app-server connection.
A separate app-server process has not been qualified as a way to update a live
desktop task or its UI association.

## Smallest useful experiment

Start with one explicit resource record and a deterministic observer. Record
host, harness, task identity, canonical path, creation or accepted transfer
evidence, users, and disposition. For a Git worktree, also bind its Git
administrative identity. Store the record outside the disposable resource.
Use named `claim`, `transfer`, `retain`, and `release` operations; a release
does not imply removal. Reconcile native attachments only through supported
controls. Keep a missing control visible as pending work.

Observe successful creation results and explicit claims first. Inspect only
events that can change a resource record. Compare this deterministic baseline
with an optional Jev classification of ambiguous handoff text over an already
enumerated candidate set. Useful questions are whether the text proposes an
ownership change, whether the receiver accepts cleanup responsibility, and
whether it names a retention purpose. Parser-derived identity and current
resource checks remain authoritative. A classifier result proposes a record
change; it cannot authorize removal.

[TypeSafe's current documentation](https://docs.typesafe.ai/concepts/how-to-build-with-system-one.md)
places typed judgments inside code-controlled workflows. Use shadow mode,
label task-local examples, keep a held-out comparison set, and measure error,
coverage, cost, and latency before selecting the classifier. Send only the
minimum approved text; transcript forwarding and live hook installation are
separate decisions. Do not choose thresholds from illustrative examples or
treat schema conformance as judgment accuracy.

Qualify missing and stale attachments, borrowed primary checkouts, same-directory
forks, accepted and unaccepted transfers, multiple users, ignored retained
evidence, duplicate events, crash/retry, archive/restore, and host changes.
Test ownership recording separately from deletion and native UI updates.

## Durability and placement decisions

The exposed tools provide no transaction that atomically binds a Provingkit
record to native task creation, archival, restoration, or deletion. Exact
co-durability with the task remains unverified. A practical first record can
survive archival and support idempotent reconciliation; it must not expire
merely because the task is inactive or absent from one listing. Decide hard
deletion and cross-host retention from measured native behavior before claiming
the record has the same lifetime as the task.

Versionkeeping owns Git resource mechanics. General task resource accounting
belongs in the existing work-stewardship effort, with Versionkeeping as an
optional Git adapter. Avoid a second independent resource manager or a new
background service until the small observer demonstrates a benefit.

The next decision is whether to build this explicit-record/shadow-observer
experiment. Automatic deletion, a classifier, live hooks, and an unsupported
desktop-state repair are outside this first experiment.
