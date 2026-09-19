# GitHub Relation-Ledger Publication Qualification

I verified that the bounded PR ledger publisher can edit an open draft, a closed
draft, and merged PRs on GitHub.com while preserving their titles, states, native
relations, and every body byte outside the authorized span. This qualifies the
historical body-publication route separately from the earlier
[native Development-link experiments](2026-09-17-github-development-relation-qualification.md).

## Live Cases

I used three retained private fixture PRs in two isolated repositories on
September 17, 2026, with owner/admin access. The Issue repository's auto-close
setting had been observed through authenticated Settings and retained by the
same task. I did not refresh it for each body edit.

| Case | Issue repository's last observed auto-close | Result |
| --- | --- | --- |
| Open draft, append one contribution entry | Disabled | Exact body verified; title, draft state, and empty native relation set preserved. |
| Merged PR, insert entries before its bot-owned suffix | Disabled | Exact body verified; all ten native links and their Issue states preserved. |
| Cross-repository merged PR, insert entries before its bot-owned suffix | Disabled | Exact body verified; both native links and their Issue states preserved; the PR repository had auto-close enabled. |
| Closed draft, replace one ledger annotation | Disabled | Exact body verified; title, draft state, and empty native relation set preserved. |
| Merged PR, add an entry for an open Issue in the enabled repository | Enabled for the added Issue; disabled for the two existing peers | Exact body verified; the added Issue stayed open and all three native links and Issue states were preserved. |

Every linked Issue in the first four cases belonged to the disabled repository.
The enabled PR-repository setting does not qualify an enabled Issue-repository
case. For the fifth case, I created one isolated Issue in the enabled repository
and added its manual link to the retained merged PR. I verified that the Issue
was open, then froze a new body-publication preimage and appended its ledger
entry. This setup was separate from the body-only publication under test.

I closed the open fixture without merging it between the first and fourth cases.
That setup action was separate from publication; the publisher changed only the
body. Ordinary body links did not create native closing relations in these cases.

For each edit, I bound the complete live preimage, stable repository and PR IDs,
and one half-open UTF-8 span. I invoked `publish_relation_ledger.py` with literal
title/body files and the explicit `not-required` review mode, then independently
reread the PR and linked Issue states. Direct byte comparison proved that the
result was exactly the original prefix, replacement, and original suffix.
The helper returned a separate relation-publication receipt.

I repeated the first three original requests before changing the open fixture's
state. Each returned `verified`, `no_op: true`, and `observed-existing`; these
results claim an observed postimage rather than another causal write.

An initial candidate appended text after a recognized bot-owned suffix. The
validator rejected it before publication. I retained that rejected plan and
inserted the ledger before the suffix, preserving all bot-owned bytes. The
independent readback harness also initially compared unequal query shapes: its
postread included an extra Issue-number field. Comparing the common identity,
URL, and state fields confirmed that the relations themselves were unchanged.

## Source And Evidence

The independently reviewed source tuple is relative to
`plugins/mergecraft/skills/`:

| File | SHA-256 |
| --- | --- |
| `writing-reviewable-pr-descriptions/scripts/validate_relation_ledger.py` | `fb398f6580a998c95e1fc6d197e4f4eb5712775ae86963722dda950d682b865c` |
| `writing-reviewable-pr-descriptions/references/relation-ledger.md` | `3beee5b03eda9fca6d0192198ae9a7089d699e7526ee1ca002195da696fdf2b5` |
| `publishing-reviewable-prs/scripts/publish_relation_ledger.py` | `29771524efa58389cf718ca735233db1844e0263a19faa104e4110fd93ff28c3` |
| `publishing-reviewable-prs/scripts/relation_ledger_receipts.py` | `e381c44a1bd09b5100fc9c0fbdb9d71283450d632effb2d328d66d133cb1b6b1` |

The test file `tests/test_mergecraft_pr_relation_ledger.py` has SHA-256
`9b96e5e3b5e84634a16caa02206e4b4874aa4406d0890b38a0ebf433bdfcf5cd`.
Its 29 focused cases and the 147 existing publication cases passed. Independent
review also exercised process interruption around journal, receipt, and renewal
installation with temporary state and a fake forge. Those checks cover local
recovery behavior; they are not live GitHub network-failure experiments.

The private evidence index binds 59 files containing literal candidates,
manifests, results, before/after responses, checks, and the qualification runner.
Its SHA-256 is
`37f7c590f458194817699ea518cf004941da7ffe039c73c0df3a66b44500c331`.
The raw evidence and fixture identities remain private. The task's selected
repair repositories received no Issue/PR content edits from these experiments.

## Limits

These are dated GitHub.com owner/admin observations. They do not establish
permission-role coverage, GitHub Enterprise behavior, concurrent edit exclusion,
or recovery from an actual post-send network failure. The API has no conditional
body write; an exact preflight and reread cannot eliminate a concurrent lost
update. The local lease coordinates only publishers sharing its receipt root.

The relation receipt provides no canonical-navigation, readiness, merge,
installation, or deployment authority. A continuing lifecycle still invokes
its normal publication owner when that evidence is required. Required witnessed
review remains unavailable for this ledger mode until its own route is supported;
the tested ordinary mode makes no witnessed-review claim.
