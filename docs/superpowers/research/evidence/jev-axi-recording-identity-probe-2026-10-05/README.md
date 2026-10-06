# Current recording identity, with coverage limits

The newer recording contains this chat's session identity and the exact call identifier of the approval question answered in this turn. That establishes a concrete local source for these current records. It does not establish complete current intent, current producer/build correspondence, or usable cost accounting. The [probe result](probe-result.json) records the supported fields and gaps for [Qualify the current-chat recording candidate with a bounded identity probe](https://github.com/nisavid/provingkit/issues/440).

## What the approved probe found

One invocation read 64 KiB from the header and 960 KiB from the captured end of the selected file: exactly 1 MiB, within the accepted ceiling. The expected filesystem identity matched on admission; descriptor and path identity matched at terminal checking. The source had the same size at those checks. The derived report retained 587 complete records as structural metadata, with no parse errors. It discarded 1,737 trailing header bytes and 12,124 leading tail bytes where record boundaries were incomplete or unknown.

Both header identity fields match the selected chat. The end window contains a function call and its output with the exact call identifier supplied in the actual approval reply. These are current task records, beyond a filename or modification-time inference. The identity join uses that independently supplied identifier; it does not assert that the captured output means approval. The actual operator reply provides the probe's authority.

Neither original annotation text matched in the windows. One current user-message record appears in the tail, but its text was not retained and the probe did not test that new approval message's contents. The missing annotation matches are a coverage limit, not evidence that the recording omitted those messages. Likewise, the observed `token_usage_record` and `token_count` shapes establish presence only: this probe retained neither their usage values nor their field semantics. Their record counts are not counts of model calls.

The header reports `cli_version: 0.159.0`, `vscode`, and `Codex Desktop` when the file began on September 30. It does not identify the currently writing build. The suffixed filename's creation, continuation, or fork mechanism remains unestablished. The concrete source selection rests on the recorded identity and current call match, not on interpreting that suffix.

## What the next contract can use

A future contract can name this selected local source and require admission to recheck its identity and current-workload evidence. It must separately bind the workload's initiating requests and amendments, relevant antecedent windows, check-time artifacts, event selection, and terminal evidence. Missing current intent or counters cannot be filled in from this probe. A summary-only route remains a distinct, narrower option.

The observation method should reject a known stale recording before ordinary work begins, retain admission and terminal identity results, account for every acquired window, and keep observer-added operations separate from the ordinary workflow. The [source investigation](../jev-axi-current-recording-source-2026-10-05/README.md) owns the missed September 29 freshness check and the proposed maintained-procedure correction. This result supplies one ordinary successful acquisition, not general collector qualification or installation of that proposal.

Research, script preparation, review, content acquisition, derived-record analysis, operator waiting, and ordinary work are separate costs. Only the original content read is quantified here. Waiting time is not operator effort, and the probe's brief timestamp interval is not whole-task latency. There is no saving or behavior-assignment result.

The independent [identity audit](identity-audit.md) and [accounting audit](accounting-audit.md) are joined in this report. Another content read, broader collection, passive observation, model experiment, or live change is outside this completed probe. The consequential-action lane retains its qualified-Daybreak hold.
