# Prepare An Existing Claude Route

Use [claude_route_nomination.py](../scripts/claude_route_nomination.py) when a
new ordinary message targets an exact existing Claude recipient, no bound native
send already reaches it, and the caller needs the launch command and native MCP
target. An already-held addressed reply stays on the
[native reply-forwarding route](native-peer-relay.md).

This procedure has two operations. `nominate` runs through the intended Claude
receiver's supported native command control. `prepare` consumes that private
record and creates the request for the existing
[Claude MCP sender](claude-mcp-sender.md). Neither operation starts Claude,
opens the endpoint, sends a message, authenticates an account, or grants
authority.

## Produce The Nomination

The agent creates a `claude-route-nomination-request-v1` JSON file with exactly
`schema`, `recipient`, `producer`, and `publication`. Recipient and producer are
identities with exactly `thread_id` and `host_id`; they must be equal. Publication
names one unused final path under an existing owned, nonsymlink mode-0700 capture
root, the effective owner UID, and the ordinary `CaptureWriter` settings.

Invoke the helper inside the actual selected receiver:

```sh
python -B "$SKILL_DIR/scripts/claude_route_nomination.py" nominate --request "$producer_request"
```

The production operation reads only these receiver controls:

- `CLAUDE_CODE_HOST_SESSION_ID`, which must equal the recipient thread ID;
- `CLAUDE_CODE_MESSAGING_SOCKET`, which must contain one normalized absolute
  socket pathname; and
- `PATH`, used to resolve the invoked name `claude` through the receiver's
  ordinary installed-command lookup.

The selected launcher path stays exactly as the lookup returns it. The helper
does not resolve a symlink, canonicalize a multi-call wrapper, replace the
invoked name, inspect credentials, or infer an executable from historical
evidence. It records `[launcher, "mcp", "serve"]`; this is the official command
shape, not evidence that the current installed catalog accepts the sender's
profile.

The helper publishes one complete `claude-route-nomination-v1` record through
`CaptureWriter`. The record binds the recipient and producer to the selected
command and `uds:` target. The final file is create-only, mode 0600, at most
4 KiB, and Unix-account-private. The safe result contains only status, locator,
size, SHA-256 digest, and `no-provider-started` closure. It omits the target and
launcher. The pathname supplies information, not authority, and mode 0700/0600
does not isolate hostile processes with the same UID.

## Prepare The Sender Request

The agent creates a `claude-sender-request-preparation-v1` JSON file with:

- `nomination`: the exact private path, size, and SHA-256 returned by
  `nominate`;
- `message`: the ordinary immutable mailbox message, including original sender,
  recipient, obligation owner, payload, authority reference, holds, and optional
  correlation ID;
- `attempt_id`, the actual submitting `actor`, and the existing sender's
  operation/stdout/stderr `limits`;
- `mailbox`: the selected private mailbox path; and
- `publication`: one unused private path and `CaptureWriter` settings for the
  sender request.

Run preparation from the authorized caller's control:

```sh
python -B "$SKILL_DIR/scripts/claude_route_nomination.py" prepare --request "$preparation_request"
```

Preparation opens the exact nomination without following the final symlink. It
requires the supplied size and digest, stable file identity, one hard link, the
effective UID, a mode-0600 record, and an owned mode-0700 parent. It validates
the complete record, reapplies the normalized socket rule, and requires the
message recipient to match the nominated recipient. It preserves the launcher's
invoked name and command bytes.

The operation initializes the private mailbox only when its path is absent,
then plans the immutable message through `Mailbox.plan`. An existing mailbox is
reused and must retain the same message content. It builds the sender request
from the ordinary inputs and validates that request with the actual
`claude_mcp_sender.validate` parser before create-only publication. The request's
`evidence_ref` is `sha256:<nomination digest>`; that reference identifies the
record and creates no permission. Preparation returns the request locator, size,
digest, mailbox locator, `sender: not-invoked`, the preserved-uncertainty
handoff, and `no-provider-started` closure. Raw route data stays out of stdout.

After preparation, recheck the original grant, actual submitting actor, current
holds, intended receiver, and any live receiver or account evidence owned by the
caller's native control. Then invoke the existing sender once:

```sh
python -B "$SKILL_DIR/scripts/claude_mcp_sender.py" --store "$mailbox" --request "$sender_request"
```

The sender owns claim acquisition, catalog negotiation, possible-submission
bookkeeping, one call, and owned-child closure. Preserve its refusal and
uncertainty rules. A new attempt ID, another route, or another launcher does not
make an uncertain attempt safe to replay.

## Binding Lifetime And Residual Control

The nomination has no invented expiry. Reuse it only while the caller's actual
receiver evidence says the host session, selected receiver, launcher command,
and existing messaging binding remain current. An app, account, session, or
launcher change requires a fresh receiver-produced nomination. The private file
and a successful RPC do not authenticate the recipient, provider, or account.

The first operation must run inside the intended receiver. When the available
cross-harness control cannot activate that receiver during initial setup, return
`receiver-side nomination activation unavailable` as the residual control
limit. Installation may then require one ordinary receiver-side activation,
subject to the release disposition. That gap does not require an operator to
paste a socket, launcher, request, or authority reference for each message.

Synthetic tests exercise the production acquisition and validation logic with
injected environment and launcher observations, real private files, the real
mailbox, and the real sender parser. They establish no live native-control
availability, installed launcher compatibility, credential or provider identity,
successful MCP startup, receiver receipt, handling, reply, or installed
qualification.
