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
- Use a local Claude agent's name as its ordinary first-send address. The name
  is an unauthenticated label and must equal the planned recipient's `thread_id`.
  The sender reads one `ListAgents` listing from its own `claude mcp serve`
  child, builds the address from the matching row, and records that row's name,
  reference, and kind.
  The sender makes at most one `SendMessage` call. A supplied recipient-prepared
  route takes the fallback path, and the result names the path used.
- Close the Claude sender's child as the MCP stdio lifecycle describes: close
  its input, wait briefly, then `SIGTERM`, then `SIGKILL`, waiting on its exit
  rather than its pipes, so it is no longer run to the deadline.
- Refuse unmatched, ambiguous, non-local, and stale-reference destinations.
  Disclose matching rows when resolution requires them and ask for a selection
  when a unique local reference is available. Refuse an oversized call frame in
  `prepare` before planning or publishing. On either send path, commit a definite
  pre-submission `refused` observation together with `not_delivered`. Callers can
  request a later attempt by supplying both `after_attempt` and `decision_ref`.
- Require a recognizable listing row before counting or matching it. Skip and
  count an unreadable row only when it cannot carry the requested name, and
  retain the count even if the listing fails. Refuse unaddressable names before
  claiming an attempt. Notes and pages stay strict.
- State the 2026-11-19 decision on a Claude reply waking a Codex sender, and
  that an envelope's sender and actor are claims without authority. The
  Claude sender reference points its note that the child ends after the call
  at that decision.
