# Send Through The Existing Codex Owner

Use [owner_admission_sender.py](../scripts/owner_admission_sender.py) for one
mailbox-backed message to the exact existing local Codex conversation. Load the
[mailbox procedure](native-codex-mailbox.md) and bind the selected endpoint,
original permission, current holds, private capture root, and reviewed revision.
Owner discovery is cooperative routing evidence, not authentication.

The trusted request has exactly `message_id`, `attempt_id`, `actor`, `recipient`,
`evidence_ref`, `native`, and `capture`. `actor` is the actual submitting actor;
it need not be the Codex producer recorded in a guarded nomination. The immutable
planned message separately preserves its original sender, obligation owner,
recipient, payload, authority, holds, and exchange. The sender obtains its own
attempt claim.

`purpose`, `authorityRefs`, and `holdRefs` retain the actual send bindings. Scope
is exactly `send: true`, `ownerAdmissionIntent: true`, and
`holdsSatisfied: true`. Optional `profile` and `observationSeconds` may tighten
the supported source limits. Capture settings follow the
[IPC capture contract](codex-ipc-sender.md).

## Consume A Guarded Nomination

For an ordinary entry, use an unchanged valid nomination for the same named
submitter and recipient, or acquire it through the [route-nomination
procedure](codex-route-nomination.md). Set `native.nomination` to:

- the absolute safe record path;
- its exact SHA-256 and size; and
- the caller-observed completed native invocation, including control kind,
  evidence reference, native item ID, exact task, attempt, chat, command, working
  directory, reviewed helper identity, completed status, and zero exit.

Omit `route` and `nominationRef`. The sender reads the complete record and checks
its stable regular-file identity, mode-0600 owner, mode-0700 parent, digest, size,
recipient, producer, submitter, acquisition operation and holds, per-act permission bindings,
privacy boundary, acquisition bounds, and completed native invocation. The
metadata and nomination grants name the recorded Codex producer; `routeUse`
and the request name the actual submitter. The acquisition operation and original
native invocation remain unchanged across messages. Swapped actors or acts,
a different recipient or submitter, an incomplete invocation, or a malformed
route-use binding refuses before connection.

Each message independently binds `authorityRefs` to its planned authority and
`holdRefs` to its planned holds. The caller checks that permission and those
holds are applicable now before asserting the send scope. An A-only instruction
cannot authorize B; a nomination supplies no send permission. An independently
authorized B uses its own correlation and attempt with the same route evidence.

The record has no relay deadline. The five-second value in its acquisition
evidence bounds the producer's shared sample only. At consumption, current
process and route identity, the original acquisition evidence, current message
permission and attempt, revocation status,
and applicable holds determine eligibility. An older unchanged nomination does
not authorize a new attempt.

A guarded nomination cannot downgrade to the unguarded path. Existing callers
with separately reviewed prepared-route evidence may retain the explicit
`native.route` (`endpoint`, `host: "local"`, and exact target) and
`nominationRef` form. That form preserves its existing behavior and supplies no
evidence for this producer or ordinary entry.

Invoke the contained command with the selected external mailbox and request:

```sh
python -B "$SKILL_DIR/scripts/owner_admission_sender.py" --store "$peer_mailbox" --request "$sender_request"
```

## Guard The One Connection

For the guarded form, the sender opens one connection without a protocol write,
obtains source-supported peer credentials, and compares PID, UID, GID, start
ticks, boot ID, network namespace, and executable path/device/inode with the
nominated Desktop acceptor. An unavailable or different field closes the
connection before the initialize frame. On that same matching connection, the
sender initializes, discovers the exact recipient's owner, and repeats the peer
identity check before the message.

The sender retains a pending attempt before input and emits at most one local
version-2 `thread-follower-start-turn`. Its context sets
`inheritThreadSettings: true` and `useUserMessageAdmission: true`. It predicts
neither busy nor idle and does not invoke the older state-selection engine. It
opens no probe or fallback connection and accepts no settings or account
override, remote target, attachment, or fallback operation.

The owner may use native admission or ordinary turn start. The requested flag
does not prove the branch, preservation, receipt, or processing. Generic RPC
success is possible submission; uncertain responses preserve possible effect.
Only matching receiver evidence establishes a stronger claim.

Retain original stdout, stderr, exit, invocation-owned captures, and actual
connection closure. Connection closure is separate from receiver or provider
closure and uncertain delivery. The same claimed attempt cannot reconnect or
resubmit. Reconcile through the caller's supported observations; this command
supplies neither a general receipt reader nor automatic replay.

The connected identity establishes only the nominated local process.
Cooperative owner discovery establishes routing for the exact local chat on that
connection. Neither establishes provider, account, inference-turn, or model
identity. Current Linux peer-identity support and installed-client compatibility
require separate live qualification.

Private captures rely on the caller's owned protected root and retention policy.
`CaptureWriter` writes exclusively and checks containment; exclusive creation
alone is not a private-mode guarantee. Establish the actual root/file boundary
before invocation. Current app compatibility, ordinary receiver usability, and
receiver-app recovery remain separately qualified claims.
