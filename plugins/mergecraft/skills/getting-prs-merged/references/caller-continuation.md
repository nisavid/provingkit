# Continue The Authorized Task Across Owners

A terminal handoff ends the current skill invocation. The caller is the ongoing
task that invoked that skill. It continues already-authorized work by invoking
the named owner from current state, without requesting another instruction
merely because ownership changed. This contract adds no operation owner or
mutation authority.

At each handoff, retain the exact target, original scope, separate operation
authorities, required inputs, completed receipts, and remaining gates. Confirm
that the selected operation is within those authorities, then invoke its owner
and consume only its declared result. An invocation that selects a terminal
owner does not call that owner recursively or resume from its stale snapshot.
After the owner completes, the caller starts the required fresh invocation from
live state.

Missing authority or inputs, an operator decision, conflicting ownership,
drift, an unavailable route, or an ambiguous or unknown effect gates the
affected work. Preserve evidence and report the actual gate; do not repeat a
possible mutation. A status-only request or explicit instruction to pause ends
at that requested boundary without owner dispatch.

Apply these continuations when their handoff occurs:

- **Resume:** invoke the selected conflict, focused-CI, feedback, readiness, or
  merge owner under the existing authority. Return to fresh recovery where the
  resume contract requires it. Selecting an owner is not task completion.
- **Requested review loop:** the caller invokes `tricritical:loop` once as the
  sole review loop. A bare `clean` result permits a fresh merge invocation in
  the same task. Every other result, including `clean / degraded`, preserves
  the review gate. The merge and feedback coordinators never nest this loop.
- **Focused CI:** the adapter owns only its authorized inspection, rerun, or
  scoped repair. If a verified source fix still needs a checkpoint or push,
  the caller invokes `versionkeeping:checkpointing-and-publishing-git-work`
  under separate Git authority, then refreshes the head and checks before
  resuming recovery or merge. The CI adapter does not publish Git refs.
- **Changed PR facts:** after a feedback or CI source fix, the caller routes
  the current pushed diff and changed title/body facts to
  `writing-reviewable-pr-descriptions`, then invokes `publishing-reviewable-prs`
  for the authorized text surface. Preserve other fields and the current
  draft/ready state. Verify the resulting publication before fresh merge audit.
  Unchanged text uses the read-only audit; if the new head needs a fresh
  receipt, use the publisher's separately authorized reconciliation route.
  A no-op text update cannot mint publication evidence. Missing publication or
  reconciliation authority remains a gate.
- **Remote cleanup:** after verified merge, the caller invokes
  `versionkeeping:checkpointing-and-publishing-git-work` for the separately
  authorized `remote-ref-deletion` operation bound to exact remote, full ref,
  and expected SHA. Verify its terminal result. Absent cleanup authority gates
  cleanup only and leaves the verified merge intact. Deployment stays with its
  repository-defined owner and authority.
