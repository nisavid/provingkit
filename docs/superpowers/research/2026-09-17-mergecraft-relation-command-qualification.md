# Mergecraft Relation Command Qualification

The reviewed relation command performed an exact Issue-body update and a manual
Development-link addition on isolated GitHub.com fixtures. Independent readback
confirmed both effects while preserving the Issue state, the PR body, title,
state, draft flag, head, base, and unrelated native relation. Repeating the same
authorized plan returned two observed no-ops and sent no mutation.

## Candidate And Evidence

The qualified source has these SHA-256 identities:

| Source | SHA-256 |
| --- | --- |
| `plugins/mergecraft/skills/maintaining-issue-pr-relations/scripts/relation_state.py` | `fe814d5edde02cd8bf376ab09bf41488f03931ee0a8665c96a195e70edfe784d` |
| `plugins/mergecraft/skills/maintaining-issue-pr-relations/scripts/relation_forge.py` | `b1f9c23dbe5df73b8fe07c261b6fdb933b9251df6dd2570a3b17feb46eb51d44` |
| `tests/test_mergecraft_issue_pr_relations.py` | `4e38fdf3c68e87008ef02664b61e22d56b531af389f32f2042efa13a155e49db` |

The retained private evidence index binds 14 files with SHA-256
`77b0f2352c0f9e2a4a294010b09033219d2b129e05e57eb3faab87f92b49dcd0`.
It includes the supplied request, complete observations, writer-owned exact body
decisions, plans, explicit effect authorization, reconcile results, local attempt
state, and independently acquired GitHub readback. Private fixture identities
and raw bodies remain in that collection.

## Live Exercise

The pair consists of an open Issue and a closed draft PR in one task-owned
fixture repository. The contribution is partial. The Issue repository's
auto-close setting was last observed disabled in the authenticated Settings UI
at `2026-09-17T21:03:04Z`; the command reused that task observation with its
original timestamp. The PR ledger was already correct from the independently
qualified historical publisher, so this plan required no PR publication.

| Command | External reads | External writes | Setting reads | Observed result |
| --- | ---: | ---: | ---: | --- |
| Fresh `observe` | 2 | 0 | 0 | Two complete entities, six provenance connection pages, task-cache setting reuse. |
| `plan` | 0 | 0 | 0 | Exact Issue-body span and one native addition; no PR handoff. |
| Authorized `reconcile` | 6 | 2 | 0 | Both requested effects verified through independent post-mutation reads. |
| Repeat `reconcile` | 3 | 0 | 0 | Both effects observed as no-ops. |

The applied plan identity is
`f5a946631661d60a0e03f13ee2b176e7603715f419e514ffc92bd2710cedef88`.
A separate direct GitHub query confirmed the complete candidate Issue body,
unchanged title/state, preserved PR fields, both reciprocal links, and the exact
native sets including the preexisting unrelated Issue-side link. Both result
connections were complete.

## Verification Limits

The public command's 45 tests and independent review probes cover fake-forge
errors, partial batches, receipt-bound recovery, interrupted local journals,
cache lifetimes, invalidation, and setting-generation changes during preflight.
Those tests establish local command behavior; they do not reproduce every live
network failure or concurrent GitHub edit. The live exercise above contains no
induced timeout, partial server write, or Issue closure operation. No server-side
transaction or compare-and-swap is claimed.

This exercise changes only isolated task-owned fixtures. It neither repairs the
selected repository inventory nor establishes deployed equipment activation.
