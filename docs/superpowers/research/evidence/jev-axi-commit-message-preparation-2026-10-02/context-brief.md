DONE_WITH_CONCERNS

# Commit-message context and accounting facts

The frozen jev-axi source prepares a bounded semantic check of the staged patch and message. It does not establish native delivery, useful correction, or whole-workflow cost. All nine dispatch input digests matched before and after inspection. This was source-only research using `research`; no source execution, workload, provider call, network access, or file write occurred.

## Message and diff construction

`jev-axi/src/commands/githooks.ts:299–325` reads the supplied message file as UTF-8, discards text from the first exact scissors-marker match onward, removes lines beginning with `#`, trims the first nonempty line into `subject`, and joins/trims the remaining lines into `body`. It does not bound or redact either message field in this function.

The staged input is the stdout of `git --no-pager diff --no-color --no-ext-diff --src-prefix=a/ --dst-prefix=b/ --cached`, run in the current working directory with a 64 MiB output buffer (`jev-axi/src/git.ts:6–15,26–37`). The hook supplies no unstaged patch, task request, intended scope, test results, surrounding source files, or independent file inventory. It calls `redactSecrets(diff)`, then keeps the first 12,000 JavaScript string units and appends an original-length truncation notice (`jev-axi/src/commands/githooks.ts:320–325`; `jev-axi/src/recipes/questions.ts:217–220`). This is a prefix slice, not file-aware selection; later files and hunks can be omitted or cut mid-content.

The redactor implementation is outside the frozen inputs. Its exact transformations and coverage cannot be established here. Git configuration and actual rendered patch contents were not observed. Accordingly, the message can concern changes absent from the supplied prefix, or a material omission can concern a file the checker never sees.

## Skips, questions, and consumed answers

Before evaluation, the hook returns an empty string for an empty subject, subjects beginning `Merge `, `Revert "`, `fixup! `, `squash! `, or `amend! `, a failed staged-diff load, or an empty diff (`jev-axi/src/commands/githooks.ts:307–319`). These are unsupported/skip paths, not successful semantic negatives. Missing filename validation and message-file reading occur outside the evaluation catch.

Four questions are requested: `conventional`, `describes_diff`, `focused`, and `subject_quality`. The semantic question asks whether subject plus body accurately describes the main change, including false claims and omission of that main change. The other questions concern formatting, number of independent changes, and subject usefulness (`jev-axi/src/recipes/questions.ts:196–215`).

Only `describes_diff.noul` and `subject_quality.score` are consumed by the hook. A semantic value below 0.6 adds `message-mismatch`; quality below 1 adds `vague-subject`. The model's conventional and focused answers are unused. Formatting instead uses a local regex when at least three history subjects exist and at least half of the last twenty match it (`jev-axi/src/commands/githooks.ts:32,329–364`). The accepted purpose excludes style, enumeration, and formatting from semantic success (`docs/superpowers/research/2026-10-02-jev-axi-remaining-family-acceptance.md:45,58–61`).

## Delivery and error behavior

No issues yields empty output. Issues yield TOON fields for warning/block status, subject, rounded match value, and generic help. Default behavior warns; `--strict` sets exit code 1 only for `message-mismatch`. Vague subject and formatting findings alone do not trigger that block (`jev-axi/src/commands/githooks.ts:329–354`; `jev-axi/src/commands/common.ts:45–56`). The generated shell hook invokes commit-msg without strict and exits successfully when jev-axi is unavailable (`jev-axi/src/commands/githooks.ts:377–381`).

Evaluation receives a 20-second per-attempt timeout and zero retries. Exceptions from evaluation return a skip message, including missing/rejected authentication and other service errors, without setting the strict mismatch exit code (`jev-axi/src/commands/githooks.ts:31,35–38,323–328`; `jev-axi/src/client.ts:67–80,249–258,293–336`). Missing/malformed answer handling after evaluation is outside that catch. CLI rendering/exit handling and actual harness consumption are outside the inputs.

## Cache and accounting limits

The client defaults to caching; its key hashes the resolved requested model, supplied state, and all questions. Cache disabling, TTL expiry, and locally recorded alias changes govern reuse; default TTL is 24 hours. Alias changes become known through live successful calls, not independent freshness checking (`jev-axi/src/client.ts:94–146,219–245,268–285`; `jev-axi/src/config.ts:28–34,165–167`).

Successful live evaluations pass concrete model, provider token counts, measured call duration, question count, project, and all-answer band counts to `recordUsage`. Hits pass original token counts, cached=true, and duration zero. Command identity is the shared `git-hook`, and question count includes the two unused answers. Failed calls throw before this recording path (`jev-axi/src/client.ts:223–290`).

The hook discards returned usage, duration, model, and cache status, bypassing `finish`'s usage/raw rendering (`jev-axi/src/commands/githooks.ts:325,349–354`; `jev-axi/src/commands/common.ts:24–42`). Ledger persistence, monetary calculation, SDK serialization, and actual billing are unverified because their implementations are outside the inputs. Configured price defaults/overrides are source settings, not verified current prices (`jev-axi/src/config.ts:5–10,35–36,180–182`). Package source declares version 0.7.2; the lock resolves TypeSafe SDK 0.6.0 (`jev-axi/package.json:1–3,49–53`; `jev-axi/pnpm-lock.yaml:14–19`).

Context preparation, cache lookup, skipped/error attempts, interruptions, review, recovery, operator effort, and maintenance remain unmeasured. Native writing/review workflow and useful correction remain prerequisites for the comparison contract, not findings established by this inspection (`docs/superpowers/research/2026-10-02-jev-axi-remaining-family-acceptance.md:99–126,158–162`).
