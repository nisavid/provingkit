# Staged-change and push-review input inventory

This source inventory identifies what the two hooks can supply to a later comparison: staged patches, one selected push update, typed scores, and partial call accounting. It establishes no native delivery, useful correction, removed review work, security effectiveness, or assignment. All jev-axi references below are pinned to `a1fe6190c65b528ad5b85cbe276fd4b68bdeb236`.

## Facts: staged changes

`preCommitHook` calls `loadDiff({ staged: true })`, which uses `git diff --cached`; it does not load unstaged content, untracked files outside the index, complete files, callers, requirements, test results, or earlier reviews. `parseDiff` splits unified patches and counts added/removed lines. An empty parsed result or diff-loading error returns an empty string. [Staged input][staged], [diff loader/parser][git].

Before semantic review, `scanAddedLines` scans added lines using `findStrongSecrets`. Local matches set exit code 1 and return file/line/kind records unless `--block-on none` is selected. This return precedes semantic calls and the 60-file limit. `reviewFiles` separately runs strong and possible-pattern scans, then applies `redactSecrets` to each truncated patch. These are wiring facts about regex rules and replacement, not evidence that a credential is real or that transmission is protected. [Hook branches][staged], [local scanning][scan], [pattern functions][patterns].

`reviewFiles` assigns file IDs and truncates each patch at 6,000 JavaScript string units, appending its original length. It estimates tokens as `ceil(length / 2.6)`, adds 200 per file, and packs chunks against a 24,000 estimate. Each chunk receives only its files' paths and prepared patches. Five questions per file ask risk, missing tests, secrets, leftovers, and behavior change. Scope and kind are asked only in the first chunk; consequently their input may omit later chunks. Concurrency defaults to four, with an environment override capped at sixteen. [Review construction][review], [questions/limits][diffquestions], [token estimate][tokens], [concurrency][concurrency].

The per-file consumers are explicit: risk sorts rows and flags at 1.5; secrets and leftovers flag at 0.6; missing tests flags at 0.6, or 0.9 if any recognized test file appears. A matching filename stem suppresses missing-test flags; recognized test paths suppress that flag for themselves. This is filename/diff logic, not evidence of executed or adequate tests. `behavior` has no decision or displayed-output consumer in `reviewFiles`; it remains in raw answers, cache, and aggregate band accounting. Risk confidence produces a band that the hook omits from its displayed rows. [Aggregation][aggregation], [test-path rules][git], [band accounting][bands].

The hook prints kind and either an “ok” line or flagged file/risk/flags rows with help. Scope-level help appears only after another flag or local match avoids the early return; scope alone does not trigger output of that suggestion. Default semantic flags warn; `--block-on flags` sets exit code 1 in the flagged-output branch. Although the shared parser accepts `--json`, `--model`, `--no-cache`, and threshold flags, this hook does not forward them to evaluation or use JSON rendering. Each chunk gets command `git-hook`, a 20-second per-attempt timeout, and zero retries. A review rejection becomes a skip message; other concurrent chunks may already have completed. [Hook output][staged], [shared flags][args], [review construction][review].

## Facts: pushed changes and repetition

`parsePushUpdates` reads stdin records containing local/remote refs and SHAs, ignores short records, and excludes all-zero local SHAs (deletions). Existing refs use `remoteSha..localSha`; new refs use `localSha --not --remotes`, relying on local remote-tracking refs rather than a fresh remote query. Commit enumeration caps at 51. Existing-ref diffs compare the two endpoint trees; new-ref diffs compare the selected oldest commit's parent with the local tip, falling back to the empty tree for a root. This supplies a net diff, not each commit's patch. Errors in range construction return no candidate. [Update/range functions][range].

For multiple updates, `prePushHook` selects the candidate with the largest enumerated commit count; ties retain the first. Other updates are not combined. The payload branch is the selected remote ref with `refs/heads/` removed. `--range` replaces stdin selection, and `--file` takes precedence over it, uses the patch pathname as branch, and supplies no subjects. Both explicit modes bypass push-seen state. These branches do not establish push-wide coverage. [Selection][selection].

More than 50 enumerated commits or 60 parsed files produces a skip line. A 51-commit enumeration is sufficient to trigger the limit but does not report the full count of a longer range. Empty results and non-file diff failures return an empty string; patch-file errors propagate. The code redacts the net diff, then truncates it at 20,000 string units. Paths and line counts come from the untruncated parsed diff. The single evaluation receives branch, commit subjects (SHA fallback on subject-read failure), file summaries, and bounded diff. It receives no commit bodies, prior findings, release checklist, operational execution evidence, or push-result receipt. [Payload/limits][pushpayload].

All four push answers have threshold/output consumers: migration without note, sensitive area, generated files edited by hand, and leftovers. Migration asks whether subjects or diff mention rollback/deploy/ordering; sensitive-area asks about touched code. Neither supplies the external obligation or completion evidence required to establish missing operational work. The fourth question's name includes “unreviewed”, but its instructions ask about added markers; no earlier-review record enters the request. Warnings start at 0.6; optional `--block-on flags` sets exit code 1 for a raised score at least 0.8. JSON exposes all scores and raw result metadata; ordinary output exposes raised concerns, or a “nothing flagged” line. [Push questions][pushquestions], [Output consumers][pushoutput].

The push-seen key is repository root, selected remote ref, and local tip. It excludes destination remote, old remote SHA, configuration, model, and question identity. After any successful evaluation, including a cache hit or no raised concerns, the key is recorded before the optional block decision. Thus a previously blocked evaluation can select the quiet return on an identical later invocation if the record persists. No accepted-push receipt is required. Lookup accepts any numeric timestamp; the 30-day pruning occurs only during writes. Reads/writes are best effort. [Seen state][seen], [Ordering][pushoutput]. This is a conditional source consequence, not an observed native push outcome.

## Facts: cache, accounting, and output boundary

Both hooks use `evaluate` with cache enabled by default. Cache identity hashes requested model, state, and questions; TTL defaults to 24 hours, and `JEV_AXI_NO_CACHE=1` disables reuse. Hooks ignore their parsed `--model`/`--no-cache` flags, so model selection instead follows environment/configuration/default resolution. Alias invalidation uses the last locally recorded live resolution, not a fresh provider lookup on every hit. [Cache identity/freshness][cache], [Evaluation][evaluate], [Defaults][defaults], [model resolution][model].

Successful live calls and cache hits append best-effort usage records: time, generic command `git-hook`, resolved model, input/output tokens, elapsed call milliseconds, question count, cache status, project basename, and aggregate answer bands. Hits repeat historical tokens with zero milliseconds; totals separate these as “saved” tokens. Failed calls, skipped hooks, local-only scans, input preparation, downstream repair, and operator effort have no records in this path. Generic command/project fields supply neither hook-family attribution nor unique episode/attempt identity. Concurrent call milliseconds do not establish synchronous wall time. [Evaluation][evaluate], [Ledger/totals][usage].

Pre-commit discards its returned result metadata from displayed output. Pre-push calls `finish` for JSON or flagged output, including usage; its ordinary no-concern early return omits that metadata. CLI wrapping returns command strings through an SDK runner and a stdout sink that suppresses standalone blank lines. Installed scripts invoke the commands when the executable exists. Actual harness consumption and SDK behavior remain unobserved. [Rendering][render], [CLI boundary][cli], [Installed scripts][scripts]. Existing tests contain fake-service assertions for selected branches; they were read, not run, and provide no new runtime or utility result here. [Test source][tests].

## Hypotheses and missing native observations

The accepted exploratory portfolio keeps focused staged-contract review and reconciliation of operational obligations eligible, including earlier/on-demand delivery and measured operator verification or resumption benefit. Ordinary review, linters/tests, deterministic path selection or release manifests, and omission remain alternatives. These are hypotheses, not selections. [Portfolio][portfolio].

Focused staged review would need a supplied unresolved question, its producer, applicable requirements, necessary callers/full-file context, candidate identity, and existing verification. Push reconciliation would need complete intended ref coverage, current obligations, completed operational work, and earlier dispositions tied to the changes. Their absence here limits what the present payload can establish; adding them entails preparation/refresh costs.

Before a future runnable contract, the smallest missing native record is a bounded ordinary preparation episode linking intended staged content and pushed refs to existing review/check work, applicable obligations, actual delivered findings or skips, any correction, repeated/blocked-push outcome, and terminal task evidence. Accounting must retain attempts and omissions, separate shared diff work from incremental push work, and expose operator effort, constrained-model usage, latency, and money as measured or unknown. No such episode was executed or inspected here.

The maintained comparison contract was explicitly consulted for context-before-judgment, ordinary/deterministic/omission comparators, failed/skipped-attempt retention, and complete accounting. It is suitable for a later bounded benefit or verified-replacement contract once native inputs, supported cases, identities, consumers, and acceptance are settled. It supplies no execution authorization here. Security-related qualification remains separate and open. [Comparison procedure][comparison], [Accepted purposes][acceptance].

[staged]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/commands/githooks.ts#L41-L87
[git]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/git.ts#L25-L77
[scan]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/git.ts#L109-L143
[patterns]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/safety.ts#L35-L88
[review]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/commands/diff.ts#L100-L137
[diffquestions]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/recipes/questions.ts#L13-L76
[tokens]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/items.ts#L15-L25
[concurrency]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/concurrency.ts#L6-L23
[aggregation]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/commands/diff.ts#L138-L170
[bands]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/client.ts#L83-L91
[args]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/args.ts#L13-L37
[range]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/commands/githooks.ts#L89-L139
[selection]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/commands/githooks.ts#L185-L234
[pushpayload]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/commands/githooks.ts#L236-L272
[pushquestions]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/recipes/questions.ts#L231-L275
[pushoutput]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/commands/githooks.ts#L274-L295
[seen]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/commands/githooks.ts#L141-L174
[cache]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/client.ts#L94-L147
[evaluate]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/client.ts#L214-L290
[defaults]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/config.ts#L28-L37
[model]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/config.ts#L165-L173
[usage]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/usage.ts#L11-L118
[render]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/commands/common.ts#L24-L56
[cli]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/cli.ts#L87-L151
[scripts]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/commands/githooks.ts#L371-L387
[tests]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/test/githooks.test.ts#L126-L273
[portfolio]: https://github.com/nisavid/provingkit/blob/450e3556c803182569c8b85f19907aaf499bcd5a/docs/superpowers/research/2026-10-04-jev-axi-exploratory-opportunities.md
[comparison]: https://github.com/nisavid/provingkit/blob/450e3556c803182569c8b85f19907aaf499bcd5a/.agents/skills/handling-sys1-incidents/references/comparison-contract.md
[acceptance]: https://github.com/nisavid/provingkit/blob/450e3556c803182569c8b85f19907aaf499bcd5a/docs/superpowers/research/2026-10-02-jev-axi-remaining-family-acceptance.md
