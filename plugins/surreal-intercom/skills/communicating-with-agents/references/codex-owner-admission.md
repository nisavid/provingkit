# Send Through The Existing Codex Owner

Use [owner_admission_sender.py](../scripts/owner_admission_sender.py) for one
mailbox-backed message to the exact existing local Codex conversation. Load the
[mailbox procedure](native-codex-mailbox.md) and bind the selected endpoint,
original permission, current holds, private capture root, and reviewed revision.
Owner discovery is cooperative routing evidence, not authentication.

The trusted request has exactly `message_id`, `attempt_id`, `actor`, `recipient`,
`evidence_ref`, `native`, and `capture`. The message is already planned and
immutable; the sender obtains its own claim. `native.route` supplies the nominated
endpoint, `host: "local"`, and exact target. `nominationRef`, `purpose`,
`authorityRefs`, and `holdRefs` retain the actual bindings. Its scope is exactly
`send: true`, `ownerAdmissionIntent: true`, and `holdsSatisfied: true`.
Optional `profile` and `observationSeconds` tighten the supported source limits.
Capture settings follow the [IPC capture contract](codex-ipc-sender.md).

Invoke the contained command with the selected external mailbox and request:

```sh
python -B "$SKILL_DIR/scripts/owner_admission_sender.py" --store "$peer_mailbox" --request "$sender_request"
```

The sender initializes one connection, discovers the exact recipient's owner,
retains a pending attempt before input, and emits at most one local version-2
`thread-follower-start-turn`. Its context sets `inheritThreadSettings: true` and
`useUserMessageAdmission: true`. It does not predict busy versus idle or invoke
the older state-selection engine. It accepts no settings/account override,
remote target, attachment, or fallback operation.

The owner may use native admission or ordinary turn start. The requested flag
does not prove the branch, preservation, receipt, or processing. Generic RPC
success is possible submission; uncertain responses preserve possible effect.
Actual matching receiver evidence establishes stronger claims separately.

Retain the original stdout/stderr/exit, invocation-owned captures, and actual
connection closure. Connection closure is separate from receiver or provider
closure and from uncertain delivery. The same claimed attempt cannot reconnect
or resubmit. Reconcile through the caller's supported observations; this command
supplies neither a general receipt reader nor automatic replay.

Private captures rely on the caller's owned protected root and retention policy.
`CaptureWriter` writes exclusively and checks containment; exclusive creation
alone is not a private-mode guarantee. Establish the actual root/file boundary
before invocation. Current app compatibility, ordinary receiver usability, and
receiver-app recovery remain separately qualified claims.
