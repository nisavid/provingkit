# Code RC source addendum: native address and Stop-hook paths

**DONE_WITH_CONCERNS.** The acquired RC artifact establishes a source path from an exported inbox socket to an explicit native `SendMessage` address, and a source path that constructs and dispatches Stop-hook input with Code identity and final assistant text. Those gaps are narrower than the first report could establish. The intended Desktop task, actual selected executor, effective hook configuration, and fresh live binding remain unobserved.

This addendum is independent of the other current lane and prototype. It supplements the frozen first report without changing its acquisition proposal or authorizing execution.

## Artifact identity

I recomputed the decompressed artifact’s SHA-256:

```text
dee301c3e248c62137cc15aafc2781bd5316c66720dd890d72e0054a024ce7d9
```

Its size is **243,059,896 bytes**, and its mode is **0600**. The coordinator’s acquisition record binds it to the [public Code 2.1.284 RC artifact](https://downloads.claude.ai/claude-code-releases/rc/16cbb4ddeeb473f57fd8d5b713764903d7928e66/2.1.284/linux-x64/claude.zst), compressed SHA-256 `20b1b16df81e34abc68bef87c5a8433106f0cf4e84b2dd507e37bb7978cbd6f2`.

Embedded source identifies version **2.1.284**, commit `16cbb4ddeeb473f57fd8d5b713764903d7928e66`. This matches Desktop’s embedded release target. It does not identify an observed receiver executable. Desktop’s override, preseed, fallback, update, and launcher paths remain relevant.

The artifact contains embedded JavaScript modules. The offsets below address their text within the complete binary; no module was imported or executed.

## Socket binding and address representation

The inbox implementation connects several relevant operations:

- `L6o` selects the configured socket path or `V2o`’s default and delegates to `K2o`.
- `K2o` delegates to `mn`, which creates and binds the server.
- After binding and setup, `mn` assigns the actual path to `process.env.CLAUDE_CODE_MESSAGING_SOCKET`.
- The same path is converted through `nj` for outgoing address representation.
- Teardown clears the active path and exported socket value.

Primary spans are **221,440,600–221,444,000** for path selection and teardown, and **221,454,185–221,459,450** for binding and export. Startup awaits `startCrossSessionInbox` before the subsequent settings-hook snapshot in **221,294,800–221,297,650**. This supports the documented startup ordering for this source target, without proving that a particular startup successfully bound an inbox.

The address conversion is more precise than concatenating a prefix. At **199,156,500–199,157,050**, `nj` returns `uds:` followed by `R`’s encoded path. `R` preserves its specified ASCII path characters and percent-encodes other UTF-8 bytes. At **199,159,618–199,160,150**, `Eh` recognizes `uds:` and decodes the target. It also recognizes certain bare socket-path forms.

A maintained observer should therefore preserve the socket path and its correctly encoded selector as distinct values. Paths containing a literal percent sign or other encoded characters make an unqualified prefix operation an unsafe interpretation shortcut. No socket or token was read from a receiver.

## Native SendMessage accepts the explicit address

The inspected `SendMessageTool` is the `vs` definition, beginning around **229,193,264**. Its plain-text delivery path calls `Eh` on `to`.

In **229,205,200–229,209,300**, the `uds` branch:

1. uses the decoded socket target;
2. rejects its own endpoint;
3. calls imported `sendToUdsSocket` for a nonempty message;
4. reports the resulting message ID or an error.

The imported wrapper exports `VMt` as `sendToUdsSocket` at **218,488,411**. `VMt`, **204,380,143–204,381,350**, constructs the peer envelope and passes the destination to `Pe`. This is a connected native implementation path, rather than a statement inferred from address strings.

**Correction to the first report:** conversion from a projected socket to an accepted native selector is now established for this RC source target. A fresh observation that binds the intended fixture to its actual socket remains necessary.

There is also an identity-check limit. `VMt` supports optional expected-peer PID and process-start inputs, and `Pe` implements corresponding connection checks. The inspected ordinary SendMessage socket calls pass the plugin context, without supplying those optional identity values. Their presence in the transport must not be presented as an automatically active exact-process check for every SendMessage call. This is an implementation observation, not a security acceptance judgment.

## What native discovery reads and returns

`ListAgentsTool`, **228,963,500–228,964,800**, calls `listAllPeers` and then `formatForModel`. Its returned public data remains a **formatted listing string**.

The underlying discovery path is concrete:

- `dlr`, **230,810,516–230,812,000**, gathers local peers through `fOr` and creates internal descriptors carrying transport, socket address, and session data.
- `fOr`, **204,389,920–204,390,900**, reads registry records, excludes its own socket and certain spare/parked sessions, checks process state, and probes socket connectivity.
- `F` and `Q`, **204,386,076–204,388,300**, enumerate numeric JSON records in the session-registry directory and parse their contents.
- `lYo` and its peer formatter, **230,812,730–230,818,900**, format names, references, kind/status information, and a Desktop label.

Registry records include Code `sessionId`, socket path, cwd, process identifiers and start information, version, entrypoint, and optional host identity. The producer writes these fields in **200,583,800–200,586,100**.

The host identity has a source chain: retained Manager `buildSessionEnv` sets `CLAUDE_CODE_HOST_SESSION_ID` from its session argument around **1,321,600–1,322,620**. The engine’s `N6n`, around **200,587,025**, conditionally reads and validates that value. Registry parsing and candidate construction preserve `hostSessionId`, including **204,387,500–204,387,700** and **199,383,000–199,384,100**.

This improves the source inventory for the Desktop/Code/socket join. It does not create an external structured getter: the inspected public listing displays the Desktop classification but does not return those identities as separate fields.

Discovery also has a broader footprint than its formatted output. It reads registry records and performs socket/process checks. Conditional cleanup can delete stale registry records. Thus the tool’s declared read-only classification does not establish an absence of housekeeping writes, nor an exact-selected-record acquisition boundary. These operations need assessment within any later native-discovery grant.

## Stop-hook production and final-text semantics

The Stop producer is `ree`, **207,307,589–207,308,700**. For a main session it constructs Stop input using `Tc`, then dispatches through `Ok`.

`Tc`, **207,318,493–207,319,450**, supplies the Code session ID, transcript path, cwd, optional prompt ID, permission mode, agent fields, and effort. Its served-call branch produces a distinct `served:` identity, so a collector must not collapse that case into an ordinary local Code session.

The final text has defined source semantics:

- `_y`, **208,919,865–208,919,955**, chooses the last assistant record in the supplied message array.
- `mo`, **208,970,859–208,971,040**, joins text blocks.
- `ree` joins those blocks with newlines and trims the result. Empty or unavailable text becomes absent.

The field is therefore **text extracted from the last assistant record, with whitespace normalization**. It is not byte-identical raw transcript content. An acknowledgment convention can account for this transformation; it must not silently promise untouched source bytes.

The producer adds background-task and cron summaries. Those include descriptions, selected commands, and cron prompts, with per-text truncation in `oLt` and `rLt`, **207,306,400–207,307,100**. A minimal collector receives this broader event input before it can retain a smaller projection.

The normal turn-ending path supplies its completed message array to `ree` at **212,934,500–212,935,100**. Stop execution is conditional: settings hooks can be disabled, no matching hook may exist, workspace trust may prevent execution, and an aborted signal can end dispatch. Relevant spans are **207,307,589–207,308,050** and **207,364,168–207,365,600**.

The dispatch path serializes the complete input in `NAo`, **207,367,800–207,368,500**, selects command execution around **207,377,700**, and passes that serialized input to `y0`. Command spawning and stdin delivery are visible in **207,332,650–207,335,850**. This establishes settings-command-hook implementation for the source target. Actual configuration loading, reload, execution, timing, and coexistence remain qualification work.

## Refined fixture witness and remaining gaps

The existing proposed handshake remains useful: an operator acts in the intended dedicated-project Desktop task, requests a unique agreed response, and a separately authorized Stop projection observes that response with Code identity and socket.

The new source permits a stronger candidate comparison:

```text
operator-selected fixture handshake
    → observed Code session ID and socket
    → correctly encoded native address
    → uniquely matching current Desktop metadata Code ID
```

An optional host-session label can corroborate the Desktop relationship if the effective hook environment or an explicitly approved registry observation exposes it. Its availability must first be established; this investigation does not authorize a registry read or require adding that field to a collector.

The independent selection witness is still essential. A host label, matching title, current registry record, or socket cannot establish that the operator selected that task or consented to the notification’s purpose. Historical Code IDs remain lineage evidence, not admission substitutes.

| Question | Result after this addendum |
|---|---|
| Does this RC implement explicit native socket targets? | Yes; encoder, parser, and send call are connected in source. |
| Does it implement Stop identity and final-text input? | Yes; producer and command dispatch are connected in source. |
| Is it the actual selected executor? | Unobserved. |
| Is the intended Desktop task independently identified? | No completed witness. |
| Will the selected project hook load and execute? | Requires separately authorized observation. |
| Does Stop prove incoming delivery or correlated ACK? | No; attribution and acknowledgment interpretation remain separate. |
| Are complete preservation observations established? | No; the accepted account/model/applied-permissions/worktree/cwd obligations remain. |

The next cross-examination should challenge address encoding, the registry-versus-public-listing distinction, the lack of automatically supplied expected-process inputs, Stop text normalization, and whole-event acquisition exposure. Freeze this addendum before exchange and reconcile conclusions against these spans.

The later qualification plan still needs actual executor identity and one bounded no-send fixture observation before relying on hook behavior. Native delivery requires its own authority and evidence. Unknown, held, and refused outcomes remain distinct and never cause automatic resend.

I performed hashing and bounded static text inspection only. Some combined outputs exceeded display limits; relevant spans were reread separately. No execution, installation, edits, private receiver reads, live operations, or delegation occurred.