# Cross-examination reconciliation

**DONE_WITH_CONCERNS.** The source tracks agree on the remaining qualification gaps. The prototype needs a source-backed native-origin specimen before publication; its current matcher would exclude the inspected native notification.

I verified all seven hashes in `prototype-first/manifest.json` and ran the copied tests: **17 passed, zero failed**. Those tests validate the frozen invented specimen, not native receiver behavior. I made no edits or live observations.

References below use filenames within `prototype-first/`. Binary spans address the public RC artifact with SHA-256 `dee301c3e248c62137cc15aafc2781bd5316c66720dd890d72e0054a024ce7d9`.

## Mandatory corrections before source publication

### 1. Replace the incompatible peer-origin specimen

`reader.mjs:73–78` requires `origin.senderTaskId`. The RC origin schema explicitly assigns that field to an **in-process background subagent** and says it is absent for cross-session peers (binary `[199622900,199626200)`).

The native UDS receive producer constructs this origin:

- Required: `kind:"peer"` and `from`, defaulting to `"unknown"`.
- Conditional connection fields: `verifiedPeerPid`, `verifiedPeerProcStart`, and `selfSent`.
- Conditional envelope fields: `msg_id` and `plugin`.
- Fields extracted from a canonical peer envelope: normalized `name`, `fromSession`, `hopChain`, `fromMode`, and decoded `body`.

The connected producer is in `[221431000,221432900)`. Envelope extraction and the body-removal guard are in `[199157700,199159850)`.

**`fromSession` is not the sender’s Code session ID.** This native sending path obtains it through `N6n`, which reads the host-session environment value and validates it through `tgn`’s `local_…` pattern. It is an optional Desktop host identifier (binary `[200576850,200577330)`, `[200586900,200588100)`, and `[204380143,204381393)`). The broader origin schema also describes host-openable cloud identifiers; none should be relabeled as Code identity.

The native receive producer queues the notification with **`isMeta:true`**. Therefore `reader.mjs:58–61` would discard it even after correcting the sender field.

The receive-to-persistence path preserves that distinction:

1. Native receive builds the peer origin and queues `{origin, isMeta:true}`: `[221431000,221432900)`.
2. Shared `HE` delegates to the command queue: `[205339531,205340488)`.
3. Headless processing passes the command’s origin and `isMeta` into `JJe`: `[221007150,221009550)`.
4. `Ks` constructs a user record with both, and `Ae` retains them: `[213089150,213090300)` and `[208923600,208925500)`.
5. Headless processing records the resulting messages; `Hk` and `insertMessageChain` preserve their fields and add receiver session identity: `[221009500,221010150)`, `[209129150,209130050)`, `[209117400,209119500)`, and `[209084450,209085000)`.

The smallest source-backed notification matcher is:

- A selected receiver’s main user record;
- `origin.kind === "peer"`;
- `origin.from` equals the independently bound sender’s encoded native address;
- `origin.body` equals the complete notification specimen;
- Existing record-time and ordering checks remain satisfied.

Allow `isMeta:true` for this specifically classified notification path. Keep the exclusions for unrelated meta records and assistant ACK candidates.

Preserve bounded available origin fields, including message ID and connection provenance. `from` and `fromSession` remain sender-reported routing/navigation information; matching them does not establish authenticated authorship.

If transformation removes `body` through `Gde`, leave interpretation unknown. Do not recover it by stripping arbitrary wrappers. Add source-shaped tests for these cases. Batched inputs and other transcript record kinds need explicit interpretation policies; the current all-user/assistant validator must remain described as a restricted specimen.

### 2. Retain the validated binding or narrow the claim

`reader.mjs:16–36` validates supplied Desktop/Code identities, but its returned object does not retain either identifier. `findings.md` consequently overstates what the output preserves.

Either add a bounded binding projection to successful results or say:

> The reader validates the supplied Desktop-to-Code mapping; the caller retains that mapping alongside the result.

A published result should make its selected receiver binding inspectable without relying on an unstated reconstruction from inputs.

### 3. Describe Stop’s text and freshness precisely

The hook’s receipt-time checks are useful, and it correctly retains `producer_event_time_unobserved`. Keep that gap diagnostic for an unqualified candidate; do not call the candidate a fresh producer ACK.

The RC Stop producer chooses the last assistant record, joins its text blocks with newlines, and trims the result. It does not expose untouched transcript bytes (binary `[207307500,207308900)`, `[208919865,208919995)`, and `[208970859,208971099)`).

Describe `hook.mjs:34–36` as:

> Exact comparison against the normalized `last_assistant_message` field.

The supplied correlation ID is a caller-selected rule label, not a correlation parsed from Stop input. Add a fixture reflecting the producer’s normalization. The complete Stop input also includes background-task and cron information; retaining a minimal projection does not narrow what an activated collector receives.

### 4. Publish the combined getter coverage accurately

The engine supplement supersedes initial uncertainty about handler implementation:

- Rules/directories come from live Code context, including represented MCP-server-policy and host-credential rule sources.
- `get_settings.applied` exposes specifically named applied values.
- `get_status` returns display rows, current engine cwd, and local credential metadata.
- Its permission input produces an auto-mode-server row, not raw permission mode.
- Context usage resolves a configured model with permission-mode adjustments, not an individual retry model.
- The inspected StatusLine constructor/subscription path belongs to the UI.

Relevant binary spans are `[221225050,221226950)`, `[231927050,231928958)`, `[221193767,221194400)`, `[232758900,232759575)`, `[220676180,220677000)`, and `[226603350,226605900)`.

## Later qualification gaps

The identity supplement establishes encoded socket addresses and a native SendMessage parser/send path. The old source-level selector-conversion gap is closed. The current hook projector still has no socket/environment input, so it cannot demonstrate that binding.

A later authorized fixture must establish intended-task selection, the actual executor, effective hook loading, and fresh Code/socket/host binding. Explicit socket targeting does not require broad native discovery merely to construct the selector. If discovery is chosen, its registry reads, probes, and possible cleanup need their own acquisition assessment.

Native SendMessage does not automatically supply the optional expected-process checks found in its transport. Stop receipt likewise supplies no producer timestamp or completed replay rejection.

Full endpoint state remains incomplete: account authentication, remaining Desktop permission inputs, registered worktree binding, and same-query sampling still need evidence. Separate getters are not an atomic snapshot. These obligations belong to initial qualification and affected requalification; the source findings add no interval-wide preservation requirement or automatic resend behavior.