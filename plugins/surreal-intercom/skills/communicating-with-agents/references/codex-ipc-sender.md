# Codex IPC sender and original-attempt reconciliation

Submit one explicitly peer-labelled mailbox message to an independently nominated, loaded, busy Codex task, or inspect receipt of its original attempt. The command uses the existing mailbox and versioned peer envelope; it adds no queue. Native-owner interfaces remain preferred where their actual access has been established.

## Establish the invocation

Load the original operator grant, existing valid transitive scope, applicable holds, exact current peer binding, reviewed source revision and supported native profile. A caller record, stored task ID, title, serialized authority reference or successful connection does not authenticate the peer or create permission. Verify required authority through its original source. Preserve the original message, grants and holds; the forwarding actor is separate from the original sender and obligation owner.

Use an independently nominated existing endpoint and legitimate access method. The command does not discover a GUI owner, scan processes/configuration, start a server, or qualify another server as attached to the selected task. Bind the endpoint's host/conversation IDs to the mailbox recipient before use. A new build is unassessed, not automatically incompatible; carry applicable evidence forward with justified graduated checks and isolate demonstrated failures to their affected functions.

Whole acquired frames can include private conversation history, work contents, tools/settings and routing metadata. A small projection does not narrow those acquired bytes. Bind exact paths, actual acquisition/capture settings, complete resource forecasts, source compatibility, consent and closure in the owning live proposal. Source/synthetic tests supply no live access, provider turn, input, installation or ordinary adoption grant.

## Prepare the mailbox and request

Use the existing reviewed [mailbox procedure](native-codex-mailbox.md). Initialize only a deliberately new owned store. Plan the immutable message through its public command; include message/exchange identity, original sender, recipient, obligation owner, unchanged payload, original authority reference and hold references. Do not replace an existing store or change an original attempt to obtain another claim.

The trusted UTF-8 request object contains exactly:

| Field | Required value |
| --- | --- |
| `message_id`, `attempt_id` | Existing planned message and one immutable attempt identity. Native request/client-message correlation identifies that attempt; envelope exchange correlation stays distinct. |
| `actor`, `recipient` | Exact `thread_id`/`host_id` records. Actor names the actual current submitting/reading actor. Recipient must equal the planned recipient and native route. |
| `evidence_ref` | The current invocation's evidence reference, without adding authority. |
| `native` | Explicit `route` (`endpoint`, `host`, `target`), `nominationRef`, `purpose`, `authorityRefs`, `holdRefs`, `scope`, and optional `profile`/`observationSeconds`. |
| `capture` | Explicit owned existing `run_root`, finite `allowance_bytes`, `terminal_provision_bytes: 524288`, and nonnegative `later_forecast_bytes`. |

Fresh submission requires `scope.send`, `scope.acquireLoaded`, `scope.holdsSatisfied` and `scope.busyOnly` true under the actual grant and checked holds. Read-only reconciliation requires `send: false` and `acquireLoaded: true`; it retains the busy-only source-profile declaration without requiring the task still be busy for a read. The command checks cooperative declarations; they are not permission enforcement.

The [sender command](../scripts/codex_ipc_sender.py) accepts the outer request and compact original records with the source profile's 1 MiB ceiling plus an overflow byte. Native defaults are 64 KiB/frame, 256 KiB total wire, 64 events, an 8 KiB projection and ten seconds maximum state-observation age. The default per-exchange observation wait is one second; explicit supported waits are positive and at most ten seconds. Assess changed limits with the owning proposal; no refusal permits an automatic increase. Acquiring, decoding, serializing, retaining and returning data have distinct costs.

Capture writes are invocation-owned and create-only. The allowance controls this invocation's new writes; retained evidence is managed separately. The 512 KiB terminal provision and later-work forecast reserve filesystem headroom. They do not cap process memory, total execution time, or native stdout/stderr redirects. Serialization can occur before a disk check. Current trusted-input/file/OS observations provide no hostile race containment or universal deadline guarantee.

## Submit once

From the reviewed source checkout, use its documented interpreter form; do not add Python `-I` or change sibling import resolution:

```sh
python -B plugins/surreal-intercom/skills/communicating-with-agents/scripts/codex_ipc_sender.py --store "$peer_mailbox" --request "$sender_request"
```

Retain the original foreground invocation, exit, result and exact own capture paths. Follow that invocation through its native continuation if exposed; loss of the result is not permission to start it again. A claim records uncertainty before acquisition/input. The command selects only an eligible busy turn, retains the immutable pre-write attempt, and submits at most one steer. An idle or unsupported target is refused; there is no idle-start fallback or activity created to make a target busy.

Interpret the reached stage, not exit zero alone. A successful RPC without correlated receiver evidence is possible submission. A correlated accepted native server-linked message can establish receipt at that source's scope; it establishes no acknowledgment, handling, fulfillment, current complete history or work preservation. Retain proved evidence and unknown outcomes. The mailbox's original obligations and observations remain authoritative for prior attempts.

An identical repeat cannot claim another attempt. Its `claim_not_acquired`/`not_attempted` reports no new action by that invocation; it does not negate a prior submission or receipt. Read the existing mailbox rather than infer nondelivery. A new identity, capture directory or request file does not authorize a resend.

## Inspect the original attempt before acquiring again

Use the saved projection first. It must bind its native correlation, host, target, owner and connection generation to the immutable original attempt. A correctly bound retained receipt is historical evidence, not a new observation; it needs no further connection. Absence or incomplete/mismatched evidence remains unknown.

When the owning grant permits one further read, select the exact original `attempt.json` and sibling `rpc.json`, a new owned capture plan, the same original message/attempt/peer, and the current reader actor:

```sh
python -B plugins/surreal-intercom/skills/communicating-with-agents/scripts/codex_ipc_sender.py --store "$peer_mailbox" --request "$reader_request" --mode reconcile --original-attempt "$original_attempt"
```

This operation reuses a valid saved receipt or performs the permitted read-only acquisition. It never claims a new attempt, starts/steers a turn, or resends. A receipt can advance the existing mailbox attempt to received; it does not fabricate handled/completed. Original attempt/RPC bytes stay unchanged. The current compact-record profile requires intact originals for a new acquisition; a missing original input remains an explicit unknown/gap, never a fabricated replacement record or proof of nondelivery.

A receiver's synthetic waiting activity supplies a send opportunity; read-only reconciliation does not inherently require continued waiting. Its actual access interval and any reads after waiting ends must be separately included in the live grant. Do not reset a deadline, infer permission to read subsequent work, or spend a prior grant again.

## Record closure and hand off

Retain the earliest diagnosis, completed prefix, rejected length/ceiling/offset when available, later capture failures and missing evidence separately. Never replace an existing artifact to make finalization pass. An output failure can leave the durable outcome unknown even when the owned process has ended.

Report original foreground termination and actual owned connection closure. `closed` concerns this invocation's stream; it does not attest receiver termination, descendant control or an unfollow acknowledgment. Missing native/process closure remains an open resource obligation. Notification uncertainty can remain after verified owned closure under the owning proposal's explicit terms. No timeout, missing capture or absent message justifies a resend.

Return the message/attempt identities, current invocation mode and actor, reached evidence stage, source/time/completeness limits, original artifact identities, actual exit/closure, and next owner for any unresolved obligation. Reconcile the affected catalog batch through `updating-cross-harness-catalog`; keep source correctness, live qualification, installation and release as separate outcomes.

## Separate explicit idle-intent prototype

The separate `codex_ipc_idle_sender.py` entry is a source/synthetic prototype. It does not change the ordinary busy-only command, select an operating fabric, or authorize a live operation. Load the same mailbox/capture/authority requirements before evaluating it.

The request has the same outer shape as the busy sender, with `scope.idleStartIntent: true` and no `busyOnly` member. It supports submission only, not original-attempt reconciliation through this entry. The fresh exact-owner snapshot must identify idle runtime, no active turn, and explicit default/user thread kind/source. Conversation mode is observation metadata, not an invented default-mode eligibility rule. Unsupported or missing profile evidence remains a refusal; an earlier possible submission remains unknown.

The entry sends at most one native start request. It places the immutable attempt ID in `turnStart.request.clientUserMessageId` and `inheritThreadSettings: true` in `turnStart.context`, with no caller model, permission, cwd/workspace, account, admission or service override. It never switches from a busy refusal or uncertain attempt to an idle start, sends a fallback steer, or retries. The native owner performs its own inherited preparation; this is not a measured runtime-preservation claim.

An idle observation is not an atomic compare-and-start guard. The source profile excludes the inspected admission branch only under its observed default/user conditions; actual state can change before native dispatch, and the server’s busy-start semantics remain unqualified. A later concrete method/live decision must address that limit before any actual use.

The prototype reports possible submission after the native write boundary and keeps receipt unknown even when the RPC succeeds. It retains actual RPC result bytes without inventing a turn ID. It does not use the steering receipt predicate to claim opening receipt, handling, ACK or reply. A later independently authorized native same-chat observation can supply those stages if it proves the relevant identity and correlation. No full-history acquisition is added automatically.

Retain the exact original attempt, observed profile/revision/time, request/client correlation, RPC, captures, public mailbox state, foreground exit and owned closure. The same claimed attempt cannot connect or submit again; that invocation’s refusal does not establish nondelivery of the original. The current idle prototype has no resend or reconciliation escape hatch.

From the reviewed source checkout, the synthetic invocation shape is:

```sh
python -B plugins/surreal-intercom/skills/communicating-with-agents/scripts/codex_ipc_idle_sender.py --store "$peer_mailbox" --request "$idle_request"
```

This example selects no live peer. Installation, actual caller/owner binding, private acquisition, provider use, sending, receiver-app recovery and operational adoption remain separate gates.
