# Versionkeeping plugin

Versionkeeping is an Agent Plugins package with a native Claude adapter. It owns task-only
checkpointing, intent-aware conflict resolution, deterministic exact-lease
publication, separately authorized remote-ref deletion, provenance-aware
worktree lifecycle, and history-preserving fork synchronization.

It owns local Git integration, fork synchronization, and separately authorized
terminal remote-ref deletion. It deliberately does not own Graphite operations;
review or pull-request creation, text, readiness, resolution, or merge
actuation; or model and delegation policy.

Checkpointing establishes the destination's contribution policy before the
first commit. Required DCO sign-offs use the authorized contributor identity;
concrete ownership or provenance uncertainty needs evidence or escalation.
Repositories without a DCO requirement keep their ordinary commit process.

## Skills

| Public name                                             | Responsibility                                                                                                                   |
| ------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `$versionkeeping:checkpointing-and-publishing-git-work` | Git/index/ref/push safety, separately authorized remote-ref deletion, completion choices, and provenance-aware terminal cleanup. |
| `$versionkeeping:resolving-merge-conflicts`             | Conflict interpretation and authorized file edits, with Git mechanics handed to checkpointing.                                   |
| `$versionkeeping:using-persistent-git-worktrees`        | Durable sibling worktree location, creation, movement, repair, and handoff.                                                      |
| `$versionkeeping:syncing-forks-with-upstream`           | Contract-aware fork synchronization that preserves upstream commit identity.                                                     |

## Package validation

From the package root, these checks use only plugin-relative paths:

```sh
python3 skills/checkpointing-and-publishing-git-work/scripts/plan_git_publication.py --help
python3 skills/checkpointing-and-publishing-git-work/scripts/execute_git_publication.py --help
python3 skills/checkpointing-and-publishing-git-work/scripts/plan_git_remote_ref_deletion.py --help
python3 skills/checkpointing-and-publishing-git-work/scripts/execute_git_remote_ref_deletion.py --help
```

The planner may fetch bounded objects and create target-local temporary refs; it
is not an installed read-only validation gate.

The ordinary publication planner and executor accept only update/create
refspecs and never delete a remote ref. Terminal remote-ref deletion is a
separate plugin-relative planner/executor route that requires a verified merge
outcome plus explicit repository and operator authorization binding the exact
remote, full ref, and expected SHA. It deletes under an exact expected-SHA lease
and completes only by verifying the ref is absent.

Ordinary publication also observes and binds the push endpoint's symbolic
default branch. A direct push to that observed ref remains blocked unless the
request carries a matching, separately verified repository policy decision
with `direct_push_permitted: true`; topic refs remain subject to the ordinary
ownership, review, verification, and exact-lease gates.

## Developing this plugin

This section is for people who want to contribute to Versionkeeping, fork it,
or work with its internals. An installed copy leaves out the topology
(`topology.json`), the evaluation corpus, the validator, and the tests; they
stay in the source repository. The
[developer page](https://github.com/nisavid/provingkit/blob/main/plugins/versionkeeping/DEVELOPING.md)
describes the source layout and repository release validation.

## License and provenance

The plugin is MIT-licensed. Its Git-publication planner and baseline workflows
are migrated from the operator-owned canonical skill stack. No third-party
source or attribution requirement was identified in the supplied inputs.
