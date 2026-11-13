# Request owner-side admission for one existing Codex chat

The maintained Surreal Intercom command sends one mailbox-backed message through the nominated local GUI owner, asking that owner to perform native user-message admission with inherited settings. The owner can reach its admission branch or ordinary native start. The requested flag does not identify which branch ran. Source tests use disposable Unix peers; no current app/backend, receiver operation, settings preservation or operating adoption is qualified here.

## Invoke the source command

Read the maintained [Codex owner-admission procedure](../../../../plugins/surreal-intercom/skills/communicating-with-agents/references/codex-owner-admission.md) for the existing mailbox/envelope/capture responsibilities. This prototype is a separate explicit operation, not a fallback from that procedure’s busy or idle command. Do not run it against a real endpoint without the separately reviewed case, applicable grant and current admission.

```sh
python -B plugins/surreal-intercom/skills/communicating-with-agents/scripts/owner_admission_sender.py --store case/mailbox.sqlite3 --request case/request.json
```

The invocation reads trusted, explicitly selected caller files. Its request has exactly `message_id`, `attempt_id`, `actor`, `recipient`, `evidence_ref`, `native`, and `capture`. The mailbox message preserves its original sender, actor, recipient, owner, exchange correlation, authority reference, holds and payload through the shared versioned peer envelope. These are cooperative records, not authenticated identity or newly granted authority.

`native` supplies `route`, `nominationRef`, `purpose`, `authorityRefs`, `holdRefs`, `scope`, and optionally `profile`/`observationSeconds`. `route` has exactly an explicitly nominated endpoint, `host: "local"`, and a target matching the mailbox recipient. `authorityRefs` and `holdRefs` retain the planned message’s actual references. Scope is exactly `send: true`, `ownerAdmissionIntent: true`, and `holdsSatisfied: true`; those declarations require their own actual authority and hold checks. Attempt IDs reserved for initialization/discovery are rejected.

This local profile emits version 2 with no non-null `hostId` in the submission body. It does not silently treat a host-qualified request as local; the inspected native protocol uses a different version when that field is non-null. Remote/host-qualified submission is unsupported by this prototype. No tool-output injection, attachments, environment replacement or settings overrides are accepted.

## Operation and evidence

The command obtains one immutable mailbox claim and records uncertainty before acquisition. It initializes one connection, discovers the owner for the exact nominated local conversation, and stores the original pending attempt before the peer-input write. It then issues at most one `thread-follower-start-turn`, with the same conversation/native thread and client message ID, one envelope text input, and `inheritThreadSettings`/`useUserMessageAdmission` in context.

It does not follow or acquire conversation history to predict idle/busy state. That avoids making the older split sender’s state-selection acquisition a prerequisite. Owner discovery is still cooperative routing evidence, not authenticated ownership or backend capability proof. App-manager preparation, default/user eligibility, ordinary-start fallback and the actual native backend must be assessed in the live proposal.

Only replies observed in the submission receive phase can contribute its RPC status; earlier acquired records remain in the full received capture. This is local acquisition ordering, not server-time or authenticated-source evidence, and it cannot exclude a previously queued frame that was not read until later. Empty success is possible submission with effect unconfirmed; an error, disconnect or timeout can leave the outcome unknown. The prototype never reports receiver receipt, processing or actual native branch from the flag or generic RPC result.

The planned message and immutable attempt remain available through the existing mailbox command. A second invocation cannot automatically reclaim or resend that attempt. Unknown outcome needs reconciliation through an actually applicable existing observation method before any separately authorized later attempt; this prototype supplies no general receipt reader, replay, method-switching or exactly-once guarantee.

The command returns the staged result and actual owned-connection disposition, retaining the original response and bounded acquisition/capture records. It reuses the maintained transport, capture writer, mailbox and envelope. Profile values can tighten its current default limits; they cannot widen them. The observation allowance is per transport exchange, not a total elapsed deadline. Source input, JSON processing and output capture have their existing distinct costs. Owned connection closure can be established independently of uncertain message effect; it is not whole-harness or provider termination.

## Source checks

The public test seam is invented mailbox/peer/route/capture records through this command and a disposable test-owned Unix peer. Assertions cover actual framed requests, stored pending evidence, output stages and owned closure. They are mechanism evidence, not a Claude/Codex live operation or a security-enforcement test. Keep temporary socket paths short enough for the platform; retain test captures separately from the temporary socket root.

```sh
python -B -m unittest tests.plugins.surreal_intercom.test_rolecasting_codex_owner_admission
```

The owning technical task is [Prototype owner-side message admission for existing Codex chats](https://github.com/nisavid/provingkit/issues/869). Its remaining review, architecture, prototype reaction and exact live-scope obligations are separate from running these synthetic checks. The independent native-attachment alternative and wider reply/recovery/adoption outcomes stay in the [technical map](https://github.com/nisavid/provingkit/issues/840).
