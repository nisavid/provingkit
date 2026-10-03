# Passive commit-observation intent review

The proposed ordinary sorting task fits the accepted prerequisite investigation and does not manufacture semantic-review work. Three retention/binding gaps should be corrected before the concrete execution contract is presented for acceptance.

All source anchors below are under `docs/superpowers/research/evidence/jev-axi-commit-observation-2026-10-02/`, unless a repository-relative path is written explicitly.

## Actionable findings

### 1. Bind the initial Git state, not only non-Git fixture files

`prepare.py:48-61,69-79` records a baseline and configures the observer/signing, but its initial-file inventory excludes `.git`. `run.py:39-48` checks only that inventory before native import. `native.py:70-81,146-181` verifies profile/native settings but does not verify initial HEAD, index/worktree cleanliness, remotes, or the fixture's hook/signing settings.

Consequently a changed Git baseline, staged content, remote configuration, or `core.hooksPath` could survive the declared initial-fixture check while changing the ordinary task or hook opportunity. This conflicts with the proposed no-remote/passive-hook fixture description and initial-fixture check (`contract.md:20-23,74-78`). It is an ordinary reproducibility gap, not a containment judgment.

Smallest correction: record and re-observe the baseline HEAD, branch, clean index/worktree, absence of remotes, and effective fixture hook/signing settings before the task prompt is sent. Refuse drift and retain the refusal. Do not claim the current non-Git hash inventory verifies those properties.

### 2. Preserve final Git evidence for interrupted episodes

`native.py:227-238` calls `git_evidence` only after collection, profile verification, and history/settings checks succeed. Its `finally` retains controller state, but not a final Git snapshot. Permission/user-input stops (`:101-103`), time/output limits, or incomplete histories can therefore leave commits and observer records outside `git-evidence.json`.

The repository remains recoverable, as `contract.md:23` says, but that is weaker than the promised retention of final Git state and commit/observation matches (`:79-80`). A commit followed by a permission stop is still a real commit opportunity; it should not disappear from the immutable episode evidence when missing opportunities and failures are later counted (`:92-97`).

Smallest correction: attempt bounded read-only Git/observer capture after native shutdown on both success and failure, retaining capture failures separately without replacing the primary stop reason. Keep incomplete native histories unqualified.

### 3. Retain preparation failures as attempts

`contract.md:64-68` promises preservation of all attempts, including preparation failures. `prepare.py:31-82` creates and mutates the fixture before writing its manifest, with no attempt receipt or failure handler. A failure during copying, Git initialization/commit, or profile discovery can leave a directory without a structured preparation outcome; failure before directory creation leaves no attempt record in this implementation.

Smallest correction: retain a distinct preparation-attempt receipt before preparation effects begin, update it on failure, and identify any partially prepared root. If a coordinator already supplies this recording, name that required wrapper and its retained artifact in the contract rather than imply that the preparation CLI provides it.

## Intent and bounds that fit

`prompt.md:1-9` requests sorting behavior, invalid-value preservation, tests, README changes, verification, and a local commit at an explicitly agreed CLI seam. It asks for no additional semantic message review, wrong message, or predetermined defect. Its keep-local/keep-project instructions settle publication and cleanup for this fixture.

`contract.md:10-13,92-98,113-114` accepts no defect, no separate review opportunity, unavailable capability, failed tasks, questions, and permission stops as findings. It distinguishes drafting from observable review and unknown internal reasoning. That matches `docs/superpowers/research/2026-10-02-jev-axi-remaining-family-acceptance.md:20-25,80-97,121-126`: source prescriptions cannot verify removable review work, and a missing tool call cannot prove its absence.

`profile.py:55-73,98-109` binds skill entrypoints and selected resource trees; `native.py:163-175` compares native skill inventory before task delivery. `contract.md:25-31,42-48` discloses unbound transitive resources and disabled ambient features. Accordingly, this is a disclosed installed-authoring profile, not qualification of every desktop feature or every possible dependency.

The source configures native workspace-write/network/temporary-directory boundaries and stops unanswered native requests (`native.py:22-29,101-115,146-181`). `contract.md:50-55,69-72` correctly limits these to a cooperative observation and acknowledges that observed limits can act after an operation begins. Child dispatch limits are distinct from provider-request or token budgets (`:33-40`).

## Accounting and evidence limits

`contract.md:100-107` retains setup, metadata discovery, local tests, native parent/child work, reviews, interruptions, and recovery separately; it leaves unavailable money, quota, operator time, isolated review cost, and child usage unknown. `native.py:104-105,233-238` retains usage events and state without inventing aggregation semantics. This fits the whole-workflow accounting requirement in the accepted family record (`:101-111`).

The claimed observed CLI version/179-entry inventory and external V2-depth documentation (`contract.md:30,38`) are not independently substantiated by these frozen inputs. Preserve their links to retained metadata/documentation evidence in the final acceptance package; source capable of collecting metadata is not the observation itself.

The three supplied test files target the accepted real Git commit-msg, preparation CLI/manifest, and run-CLI refusal/preservation boundaries. I inspected their source only; I ran no tests and claim no passing result or native efficacy. The seed application, actual installed authoring resources, prepared manifest, and metadata observations are outside this frozen review.

The contract keeps Jev service requests and jev-axi integration calls distinct and excludes both (`contract.md:6,47`; `prompt.md:12`). No behavior assignment, live configuration change, or native execution follows from this review.

All twelve frozen input hashes matched before and after this read-only review. No files were written; no source, tests, native tasks, provider calls, external actions, or delegated work ran.
