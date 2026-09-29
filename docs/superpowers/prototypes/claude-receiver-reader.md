# Desktop evidence reader: synthetic source prototype

[Open the standalone HTML prototype](claude-receiver-reader.html) to inspect
how a reader could distinguish candidate text records from incomplete or
unsupported observations. Download the HTML and open it locally; it has no
dependencies or server requirement.

This is the throwaway artifact for
[Prototype the pinned Desktop evidence reader](https://github.com/nisavid/provingkit/issues/270),
following the operator's bounded prototype decision. It remains outside the
installed Rolecasting package. Its question is whether the proposed reader's
data model can expose useful candidates while preserving the accepted evidence
gaps. It does not establish access to a real Desktop task.

## What the source experiment exercises

The HTML contains a pure `ReaderPrototype` module with `initial`, `apply`, and
`inspect` functions. The page is a thin shell around it. Its synthetic snapshots
contain Desktop-shaped metadata and JSONL text. The module parses the JSONL,
checks task/transcript identity against a supplied fixture mapping, compares
read-window and baseline observations, and extracts narrowly defined text
candidates. Every result retains `qualification: unqualified`.

The [source report](../research/2026-09-28-claude-desktop-receiver-evidence.md)
owns the installed-build evidence. The metadata names, Code transcript ID,
message role/content shape, and known filtering/coverage concerns come from
that inspection. Native-address binding, file identities, concurrent-read
snapshots, and every message in this prototype are constructed inputs. The
declared ASAR digest is fixture data; comparing it to the inspected digest does
not measure a running application. No Code SDK or Desktop module is imported.

Seven walkthroughs expose the useful and awkward cases:

| Walkthrough | Question it exposes |
| --- | --- |
| Candidate pair | Can both matching text records be shown without reporting acknowledged? |
| Echoes and quotes | Does the example text rule distinguish an assistant ACK from a user echo or quoted line? |
| Order and schema | Are an ACK before its notification, inconsistent roles, malformed content, and duplicate IDs represented without a false pair or partial success? |
| Incomplete read | Does a partial JSONL line or changing read window remain unknown? |
| Identity and history | What happens when the address, transcript ID, file identity, or retained history changes? |
| Upgrade and settings | Does a different declared build remain unsupported, and do changed stored settings expose a gap? |
| Absence and ambiguity | Can a touched timestamp or several file candidates falsely settle an unknown send? |

The example ACK body is exactly `ACK demo-notice-001`. That is a fixture rule
chosen to make echoes and quotes visible, not an adopted acknowledgment grammar
or the future public notify interface. An assistant matching that text still
needs proven receiver origin and acknowledgment meaning. The notification
fixture's peer-origin fields likewise do not establish the external native
`SendMessage` record format.

The text-only experiment returns unknown for other content shapes, including
rich tool content; it does not claim general Code transcript support. A pair
requires a notification earlier in the supplied rows than its ACK candidate.
That order is a plausibility check, not proof of causality or a complete chain.

## Limits that remain gates

This experiment checks parsing and state decisions on supplied snapshots. It
does not implement filesystem discovery, real snapshot acquisition, flush or
retention guarantees, raw transcript chain reconstruction, native-address
resolution, or effective settings observation. Two identical snapshots are
useful input checks, not proof that all receiver activity has persisted.
Unknown remains the result for absence; the prototype never authorizes resend.

Stored `model`, `permissionMode`, and `worktreePath` are displayed before and
after. Equality is not a preservation pass. There is no account-route observer,
and effective permissions can depend on more than the stored mode. Compacted
or missing history cannot stand in for original receiver records.

The source contract must still resolve reader identity, complete evidence
coverage, actual delivery and ACK representation, and all four effective
preservation observations. The separate fixture gates own any live proof.
Busy-receiver continuity remains diagnostic.

## Review and capture

I exercised the pure module with 17 constructed scenarios. The matching pair
returned `candidate pair`; user echoes plus a quoted assistant ACK left only
the notification candidate. ACK text preceding its notification remained
`unpaired candidates`. A mismatched declared build returned `unsupported`.
Partial or changing reads, replaced files, compaction, changed identity or
settings, touched timestamps without records, and ambiguous candidates returned
`unknown`. Blank JSONL records, inconsistent roles, malformed content, and duplicate message IDs
returned unknown without provisional candidates. Every result remained
`unqualified`. Both script blocks parsed, and
the notification/ACK path also rendered the candidate pair in the in-app browser.
These are outcomes of this prototype on synthetic inputs, not Desktop behavior.

The operator can drive the walkthroughs and free-play controls, inspect every
constructed input and result, and identify misleading outcomes. The prototype
ticket remains open until that reaction is recorded.
[Decide what the Desktop reader prototype permits](https://github.com/nisavid/provingkit/issues/271)
owns the subsequent adoption and source-contract decision. Keep this artifact
on its throwaway branch; no part is adopted into the maintained procedure by
the prototype's existence or a source review pass.

If a reader is later adopted, the
[Rolecasting procedure-capture work](https://github.com/nisavid/provingkit/issues/216)
must capture its actual input binding, evidence interpretation, unsupported
build behavior, and downstream invocation after qualification. This demo is
an example of the questions to retain, not a callable peer-notification method.
