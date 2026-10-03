# Protocol correction and first-attempt report review

I found no consequential source or evidence inconsistency in the frozen correction. The corrected preparation is a faithful candidate for a separately accepted native observation; it is not native qualification or permission to launch again.

Paths below share `docs/superpowers/research/evidence/`. Controller anchors use `jev-axi-commit-observation-2026-10-02/`; report anchors use `jev-axi-commit-observation-attempt-2026-10-03/`.

## Correction and local support

Controller `native.py:115-118` now declares `capabilities.experimentalApi: true` during initialization. The frozen CLI `v1/InitializeParams.json` schema defines that Boolean capability as opting into experimental methods/fields. This matches the specific missing-capability error documented by the frozen outcome and accounting audits.

`native.py:128-136` retains an RPC error envelope and raises its error before any success-response field inspection. Server rejection can therefore remain distinct from instruction-source drift. The later source/profile, permissions, exact task-delivery, history, and final-capture gates remain present (`:186-218,236-296`).

`test_profile_run.py:28-43` makes the synthetic external peer reject thread-start without the capability. Existing successful protocol cases therefore exercise capability declaration. Its new refusal case (`:195-202`) checks the retained native error code/message, absence of the misleading instruction-drift label, and absence of task delivery. Together these test sources cover the two observed omissions at the accepted runner boundary.

The coordinator reports eighteen local checks passed after red/green regressions. I inspected source and did not run them. These are synthetic protocol/local Git checks, not a second real Codex episode or model-performance evidence.

## Public report fidelity

Report `README.md:3-33` and `first-attempt.json:2-35,75-80` agree with `outcome-audit.md` and `accounting-audit.md`: initialization/model discovery occurred; thread-start was rejected; no task prompt, authoring, semantic review, new commit, observer record, or usage event was observed. The report preserves the incorrect controller label alongside the actual RPC error rather than recasting it as observed profile drift.

The 0.844029-second interval is described as a controller interval, not model latency or whole-workflow cost. Missing usage does not become a zero-token, zero-money, or zero-quota claim. Setup, discovery, tests, review, correction, and operator effort remain separate research costs (`README.md:30-33`; `accounting-audit.md:19-29`).

The public projection retains artifact identities while excluding raw private paths/profile/log content (`first-attempt.json:36-74`). Those identities support traceability, not independent access to every underlying private record.

## Task, bounds, and fresh acceptance

The ordinary sorting task remains unchanged (`prompt.md:1-17`), with no manufactured review, wrong message, or new Jev-service/jev-axi integration call. Contract `contract.md:37-80,87-95` preserves model/delegation limits, disclosed ambient-feature restrictions, native permissions, unanswered-input stops, 480-second process deadline, output/tool limits, and no automatic retry or fallback.

`run.py:28-50` still binds source/fixture/Git identities and refuses previously attempted records. Report `README.md:12,50-51` preserves the failed fixture and requires a fresh fixture and separate acceptance. Contract `contract.md:64-67` requires the reviewed published source and concrete manifest digest before execution. Nothing in this patch or review reuses the first acceptance for another launch.

This pass is bound to all nineteen inputs in `commit-observer-correction-intent` (plan SHA-256 `7badaf0dee9e57014083a1e073baef58f7a8810d6950a440dbccd12796e33d41`). Every frozen hash matched before and after review. No writes, source execution, tests, native/model runs, external calls, or delegation occurred.
