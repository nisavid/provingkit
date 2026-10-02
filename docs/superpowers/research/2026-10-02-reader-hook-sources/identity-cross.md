# Reader/hook reconciliation

**DONE_WITH_CONCERNS.** The source increment can support an explicitly synthetic reader and Stop projector. Publication needs a concrete correction to the reader’s native-origin framing and precise wording about Stop text, timing, and the new state getters. Live receiver binding and qualification remain open.

## Frozen evidence

All seven entries in `prototype-first/manifest.json` match their SHA-256 digests. I read the two frozen state reports and all six prototype contract/code/test files. Five copied hook tests passed. Two additional, entirely invented, in-memory reader probes confirmed the origin mismatch described below; I did not run the filesystem tests or execute vendor code.

Source byte spans below are zero-based, end-exclusive. `claude.bin` is the public Desktop source-target RC artifact, 243,059,896 bytes, SHA-256 `dee301c3e248c62137cc15aafc2781bd5316c66720dd890d72e0054a024ce7d9`. `sdk.mjs` is the separate stable SDK 0.3.284 artifact, SHA-256 `32d062c37b03e10870fbf839f54694545ee01bc0ec719e47078fbed76e30ef71`. I recomputed both digests. Their source findings do not identify a live executor.

## Mandatory corrections before source publication

### 1. The illustrative reader origin now has a demonstrated native mismatch

`reader.mjs` lines 58–60 exclude every `isMeta` record; lines 73–78 admit notices only through `origin.senderTaskId`. RC’s peer schema explicitly describes that field as an in-process background-subagent ID, absent for cross-session peers (`claude.bin` [199623000,199627050)). The socket ingress instead constructs peer origin with `from`, optional kernel-derived PID/process-start information, `msg_id`, and other fields, and queues the message with `isMeta:true` ([221430400,221433000)).

The stable SDK’s record filter permits peer meta records through its `cb/Jge` exception ([498374,498950), [529000,531350)); this is supporting evidence from a different artifact, not RC-wrapper equivalence. Native envelopes also have a distinct decoded `origin.body`; hooks or attachments can cause that body field to be dropped ([199157500,199159100)). Equality against arbitrary raw message text is therefore not a verified native body mapping.

My RC-shaped synthetic origin produced an ACK-only partial result with `non_main_record_excluded`. Removing `isMeta` still produced no notice, this time with no gap explaining the unavailable native-origin mapping.

Change `findings.md` and `contract.md` from merely “unobserved illustrative origin” to “synthetic adapter; the inspected native socket path uses different attribution and meta-record semantics.” Add an explicit native-schema/provenance gap to synthetic candidate results. Do not claim the current sender-task field establishes cross-session identity. If native interpretation enters this increment, supply a separate source-grounded adapter that handles verified peer meta records and preserves applicable origin fields; otherwise keep native interpretation unsupported. A fixture candidate may remain useful and unqualified.

### 2. Stop matching compares a normalized projection, not raw final-message bytes

RC selects the last assistant record, filters text blocks, joins them with newlines, trims the result, and omits empty text (`claude.bin` [207307589,207308700), [208919865,208919955), [208970859,208971040)). It does not select a last assistant record by a demonstrated “successful ACK” predicate.

Describe `projectStop` as exact equality against the producer’s normalized Stop field. Preserve that normalization fact in the presentation; do not imply raw transcript equivalence or independently verified authorship. Whole-field matching still usefully rejects substrings and quoted prefixes.

`hook.mjs` lines 17–24 check receipt age and caller-supplied coverage. They cannot date production of the assistant text. The persistent `producer_event_time_unobserved` gap is correct. Rename the test’s “current ACK candidate” wording to “recently captured ACK candidate.” Missing producer timing may remain a diagnostic for this synthetic candidate, but must prevent promotion to a fresh, post-delivery correlated ACK. Optional cwd/mode omissions may likewise remain diagnostics; they are not required ACK fields.

### 3. Update the integrated state conclusion using the engine supplement

The first state report’s missing-handler blocker is superseded for this RC source target. `list_permission_rules` reads the current permission context and returns applicable rule arrays and additional directories ([221226535,221226950), [231927050,231928958)). `get_settings.applied` contains particular runtime values, not all permissions ([221225050,221226050)).

The status route exposes a display projection of current engine cwd ([232758900,232759575)); its underlying cwd resolver can fall back to original cwd after an exception ([198480300,198481700)). Write “current-cwd producer exposed through formatted status,” not “complete raw current-cwd/worktree getter.” Model projections identify configured/resolved selection, not every inference attempt. The state addendum’s account and fallback distinctions should govern the combined report.

## Qualification gaps that remain

Desktop metadata equality is a persisted association, not a fresh selected-task witness. RC supplies explicit socket-address encoding and parsing ([199156500,199157050), [199159618,199160150)); this closes an address-conversion source gap, while selected Desktop/Code/socket binding, current process identity, and purpose consent remain unobserved. The projector’s missing environment/socket input is honest for its agreed pure interface; adding one would require a separate collector and acquisition contract.

Separate getter replies need query identity checks and per-field sampling intervals. The new Code rule producer does not cover all Desktop/browser/computer-use grants or aggregate pending mutations. Desktop’s `Kqn/Jqn` evaluators apply time-dependent grant expiry (`.vite/build/index.chunk-DuaKZOPP.js` [3692500,3693350)); unchanged stored grants therefore cannot prove unchanged effective grants.

Initial and affected requalification still need selected-executor identity, usable receiver access, authenticated account evidence, actual model meaning, effective permissions, pending changes, and registered worktree/current-cwd binding. Ordinary sends retain fresh peer/consent checks, receiver-origin delivery, and a distinct correlated ACK. Held, refused, or unknown outcomes do not authorize automatic resend.

This report is frozen source reconciliation. I made no edits, private reads, live actions, or security-control acceptance judgment. The coordinator owns implementation, final review, and publication.

---

Frozen report payload above, excluding this separator and digest footer: UTF-8, no trailing newline, 6,796 bytes. SHA-256: `8360b6d0a15c92701f71728890e296f96a1fc28466b1ca47d17696c481b4306e`.