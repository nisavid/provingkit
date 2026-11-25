# Changelog

## Unreleased

- Distinguish the current filesystem socket from older listeners that retain
  the same name after a Linux socket is replaced. Require a stable backing
  identity in both bounded samples.
- Extract communication procedures, mailbox, envelope, and directional senders
  into an independently usable one-skill plugin with contained resources.
- Preserve original message/attempt identities and conservative outcomes during
  coordinated caller migration from Rolecasting.
- Restore ordinary native route nomination and relay procedures, including
  direct-primary classification that ignores unrelated held listeners without
  weakening genuine ambiguity refusal.
- Prepare a safe, explicitly typed Codex or Claude return nomination before an
  ordinary message requests a reply, whether or not the caller waits now, while
  leaving no-reply message bytes unchanged.
- Express reply expectation and current waiting as one exclusive three-case
  contract shared by the procedure, route references, evals, and projection.
- Reclassify the complete final Codex listener set within the original
  per-observation bounds and one shared watchdog before publishing a provisional
  nomination; retain closed-record high-water counters and finite two-pass work.
- Distinguish verified bound native return reach from nomination-backed reply
  readiness, and document the exact mailbox-valid Codex and Claude `reply_route`
  fields agents derive from safe producer results.
- Carry a held reply's existing `reply_route` unchanged when forwarding it; the
  forwarding actor neither builds nor removes one.
- Let Claude route preparation accept a received reply route's `nomination`
  field unchanged, and cover a reply sent back through each route kind.
- Record a definite refusal when the Claude sender's call frame exceeds its
  ceiling, and refuse that frame in `prepare` before planning or publishing.
- Make a local Claude agent's name the ordinary first-send address: the sender
  finds it in one `ListAgents` listing of its own `claude mcp serve` child and
  makes one `SendMessage` call, refusing non-local, unmatched, ambiguous, or
  stale-reference rows before the call. A supplied recipient-prepared route
  stays the fallback, and the result names the path used.
- Close the Claude sender's child as the MCP stdio lifecycle describes: close
  its input, wait briefly, then `SIGTERM`, then `SIGKILL`, waiting on its exit
  rather than its pipes, so it is no longer run to the deadline.
- Bind the by-name send's planned recipient to the requested name: the sender
  and `prepare` refuse a recipient `thread_id` that differs from it, and the
  attempt keeps the addressed row's name, reference, and kind. The name is an
  unauthenticated label, not a session identifier.
- State the 2026-11-19 decision on a Claude reply waking a Codex sender, and
  that an envelope's sender and actor are claims without authority.
