# Proseweaving adoption and remaining source retirement

Proseweaving already has an enabled Claude registration on Hatchery, while the
earlier Versionkeeping and Mergecraft retirement still leaves aliases and
restoration routes to reconcile. Corrected personal adoption needs a handoff to
the existing Linux rollout owner, a newly bound candidate, and evidence that
each affected harness loads its replacements before source retirement.

This records findings for
[Audit targeted plugin adoption and remaining source retirement](https://github.com/nisavid/provingkit/issues/108).
It records facts and remaining decisions; it does not accept an installation,
select source deletions, or change the pinned preview.

## Evidence boundary

The repository inspection uses commit
[`147e1ddfc969b5119001488ce1556627d3b2449b`](https://github.com/nisavid/provingkit/commit/147e1ddfc969b5119001488ce1556627d3b2449b).
The local observations below were collected on **2026-09-18, approximately
02:13–02:16 UTC**. They are a bounded check of named plugin records, discovery
entries, retirement copies, and their maintained sources. They do not replace
the rollout owner's inventory. No other host was accessed. These probes made no installation, configuration,
instruction, source-retirement, or tracker changes.

The existing
[Linux rollout claim](https://github.com/nisavid/provingkit/issues/70#issuecomment-5695907259)
assigns current inventory, installation, enablement, runtime checks, retirement,
and rollback to one worker under the preview orchestrator.
[Roll out and verify the preview on Linux x86_64](https://github.com/nisavid/provingkit/issues/70)
was still open with its acceptance criteria unchecked when read for this note.
That public claim remains authoritative despite later private progress reports.

The worker task, **Verify the pinned preview on Linux**, reports that all six
Claude members were installed and compared with the accepted target files and
modes. Its latest recorded turn was interrupted; Codex, Cursor, fresh runtime
verification, cleanup, and rollback remained incomplete. This is a dated owner
report, not an independently repeated artifact comparison or runtime test. The
current metadata check below corroborates registration and enablement only.

## Bounded observations

These observations are the primary source for the current local claims in this
note. The method read selected Provingkit keys from Codex registration metadata,
Claude installed-plugin records and enabled-plugin settings; listed immediate
client cache children; used `Path.is_symlink()` and `Path.exists()` on the eleven
named retirement candidates; and inspected only matching skill-manager records.
It did not launch a fresh model session, inspect a full settings payload, or
test discovery precedence.

| Surface | Observed result | What remains unproved |
| --- | --- | --- |
| Codex | Versionkeeping and Mergecraft have enabled configuration entries and cache directories. No Proseweaving entry or cache was observed in these surfaces. | The app's resolved marketplace, fresh-session discovery, loaded bytes, and behavior. |
| Claude Code | All six preview members, including Proseweaving, have user-scoped `1.0.0` installed records, existing installation directories, and enabled settings. | Fresh-session discovery and behavior; this note did not repeat the owner's artifact comparison. |
| Cursor | The inspected plugin cache contains no Provingkit member. | Installation through other scopes or UI surfaces, CLI/IDE parity, and runtime behavior. Cache absence alone is not host-wide absence. |
| Earlier retirement | All eleven named standalone directories are absent from the shared, Codex-specific, and Cursor-specific skill roots checked; eleven recovery directories remain. All eleven Claude aliases still exist with missing targets. | Whether any additional provider exposes the behavior; whether removing each alias preserves all required clients. |
| Prose candidates | Neither `writing-for-humans` nor `writing-for-people` exists as a standalone directory in the checked roots. `writing-clearly-and-concisely`, `writing-for-agents`, both honing skills, and `reviewing-others-prs` remain in the shared root with live Claude aliases. | Behavioral equivalence, ownership of every additional provider, and safe disposition of each contribution. |
| GitHub specialists | Codex-specific `gh-address-comments`, `gh-fix-ci`, and `yeet` directories remain. | Their complete installation-manager provenance and safe replacement path. Presence is not a deletion decision. |

The eleven retirement names are the four Versionkeeping skills
`checkpointing-and-publishing-git-work`, `resolving-merge-conflicts`,
`using-persistent-git-worktrees`, and `syncing-forks-with-upstream`, and the seven
Mergecraft skills `writing-reviewable-pr-descriptions`, `publishing-reviewable-prs`,
`graphite`, `resuming-reviewed-prs`, `getting-prs-ready-for-review`,
`getting-prs-merged`, and `stacking-pr-fixups`. This matches the list in the
[dated Linux preparation](https://github.com/nisavid/provingkit/blob/089e62e306734d66187d74e7122d8ad17f418714/docs/preview/linux-installation.md#proposed-supersession-decisions).

Source inspection used `git ls-files --error-unmatch` at dotfiles commit
[`bad7fb140f39f93bf90679d9a9060e8fbb103a58`](https://github.com/nisavid/dotfiles/commit/bad7fb140f39f93bf90679d9a9060e8fbb103a58). Ten of those eleven names still have
tracked skill sources under `home/dot_agents/skills/` and Claude alias
projections under `home/dot_claude/skills/`. The exception,
`resolving-merge-conflicts`, remains recorded by the skills manager as supplied
by `mattpocock/skills`, at
`skills/engineering/resolving-merge-conflicts/SKILL.md`. Consequently, moving the
installed directories did not retire the owning declarations. A subsequent
manager operation has a route to restore them; this is an inference from the
retained declarations, not a rematerialization test.

The same bounded comparison found the active `honing-human-facing-docs` and
`honing-agent-facing-docs` entrypoints byte-equal to their dotfiles sources.
`reviewing-others-prs` was not byte-equal, so its currently installed behavior
needs its own reconciliation. The manager identifies
`writing-clearly-and-concisely` with `obra/the-elements-of-style` and
`writing-for-agents` with `mattpocock/skills`.

## Replacement boundaries

The following table identifies the decision needed for each class. The
[disposition ledger](https://github.com/nisavid/provingkit/blob/147e1ddfc969b5119001488ce1556627d3b2449b/release/source-skill-disposition/disposition-ledger.json)
settles contribution intent, not host-removal authority. The
[Linux recovery procedure](https://github.com/nisavid/provingkit/blob/089e62e306734d66187d74e7122d8ad17f418714/docs/preview/linux-installation.md)
requires an owning manager, accepted replacement, recoverable inverse, and
fresh-session verification per changed item.

| Material | Maintained owner and supported replacement | Preserved behavior and remaining evidence |
| --- | --- | --- |
| Eleven retired standalone routes and dangling aliases | Versionkeeping and Mergecraft own the successor workflows. Ten original skill/alias declarations remain dotfiles-owned; the conflict skill has a separate upstream manager. | Resolve provider precedence and intended standalone coexistence per client. Save alias objects without dereferencing them; preserve existing recovery copies. Change declarations through their owners and verify a scoped manager consistency/rematerialization check. |
| `gh-address-comments` and `yeet` | The [Mergecraft retirement ledger](https://github.com/nisavid/provingkit/blob/147e1ddfc969b5119001488ce1556627d3b2449b/release/mergecraft-retirement-contribution-ledger.json) maps their feedback, checkpoint, push, and PR-publication contributions to Mergecraft and Versionkeeping. | Their active copies need manager classification and contribution-level reconciliation. The ledger rejects filled PR creation; that behavior is not something a replacement must preserve. |
| `gh-fix-ci` | The same retirement ledger retains the independent GitHub Actions specialist behind Mergecraft's focused-CI seam. | Preserve it and its discovery route. Installing Mergecraft is not a reason to remove it. |
| `writing-clearly-and-concisely` | The disposition ledger retains the external Elements of Style owner side by side; Proseweaving supplies portable human-facing prose mechanics. | Preserve the current coexistence disposition. Honing invokes this skill; any proposed change requires an explicit disposition decision and reviewed caller coverage. |
| Human-facing honing | Dotfiles-owned document organization, reader paths, Diátaxis integration, and claim verification. | Proseweaving's generic prose contract does not replace this document-maintenance workflow. Preserve useful specialization; decide whether its prose invocation should compose with Proseweaving. |
| Agent-facing writing and honing | Independently maintained agent-instruction and discovery guidance. | Preserve these distinct consumers and contracts. Proseweaving explicitly owns prose written to people. |
| `reviewing-others-prs` and other review routes | Existing review owners, with source dispositions documented in the [review-writing reconciliation](https://github.com/nisavid/provingkit/blob/147e1ddfc969b5119001488ce1556627d3b2449b/docs/superpowers/research/2026-09-01-review-writing-cluster-reconciliation.md). | The pinned Mergecraft roster has no `reviewing-others-prs` successor. Its installed/source difference and reviewer-side authority need reconciliation before any retirement. |
| Global Codex instructions | Dotfiles template `home/dot_codex/private_AGENTS.md.tmpl`, with its generated host projection and policy tests. | Select exact overlapping spans, retain personal voice and operational authority, and verify source and rendered instructions together. The [writing-register research](https://github.com/nisavid/provingkit/issues/107) owns the semantic overlap and drift findings. |

Proseweaving's maintained portable identity is `writing-for-people`; its
Claude-native `proseweaver` agent is a thin adapter. Generic prose mechanics,
personal voice, and surface-specific contracts remain distinct in the
[plugin README](https://github.com/nisavid/provingkit/blob/147e1ddfc969b5119001488ce1556627d3b2449b/plugins/proseweaving/README.md).
The installed skill name is therefore not evidence that every writing source or
global instruction has become redundant.

## Adoption handoff

The accepted preview procedures are
[Install and update](https://github.com/nisavid/provingkit/blob/089e62e306734d66187d74e7122d8ad17f418714/docs/preview/install-and-update.md)
and
[Prepare and reverse a Linux installation](https://github.com/nisavid/provingkit/blob/089e62e306734d66187d74e7122d8ad17f418714/docs/preview/linux-installation.md).
Their consumer records the reviewed procedure revision separately from the
qualified product source, `8acd0e2af1f4508a0e2358d8e01f6a3db7a78ce3`, and each
target's accepted artifact and raw receipt. A corrected Proseweaving candidate
cannot inherit that preview's qualification merely by retaining version
`1.0.0`. The existing `provingkit` marketplace also creates a concrete collision:
replacing its source can affect already installed members and their rollback.

The next adoption decision should bind:

1. The corrected member revisions and supported target projections, separately
   from the immutable six-plugin preview and whole-Kit release claims.
2. The existing rollout owner's acceptance of the targeted handoff or an
   explicit ownership transfer before overlapping host work begins.
3. A per-item retirement matrix covering behavior, source/manager, all affected
   clients, invocation pointers, recovery, and absence of the retired route.
4. Fresh runtime evidence for Codex, Claude, and each supported Cursor surface;
   metadata alone remains insufficient. An unavailable surface is an explicit
   qualification limit.
5. Reviewed updates to the existing maintained procedures where targeted
   adoption needs a different path. Consumers invoke
   `capturing-agent-procedures` and `extending-managed-skills`, record the
   revision consumed, and return corrections to those owners.

Those are handoff and decision requirements, not a new installation procedure.
The research can close with the current uncertainty explicit; runtime acceptance,
source-retirement choices, and owner coordination remain ahead of execution.
