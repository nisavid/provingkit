DONE_WITH_CONCERNS

# Passive commit observation runtime recheck

The revised preparation resolves the earlier findings, but its fixture identity still does not bind the executable mode of the passive Git hook. Correct that before freezing the runnable manifest. All 30 input SHA-256 digests matched before and after this read-only review. I did not execute source, tests, native tasks, or provider calls, and did not write files.

Paths use `E/` for `docs/superpowers/research/evidence/jev-axi-commit-observation-2026-10-02/`, and `S/` for the supplied Codex CLI 0.160.0 protocol package.

## Remaining actionable finding

**[P1] Removing the hook's executable bit passes every pre-turn fixture check.** `E/prepare.py:79–85` makes the commit-msg script executable, but `initial_files` at lines 102–104 records only content hashes. `E/run.py:39–47` compares those hashes and a semantic Git snapshot; `E/git_state.py:11–16` includes the configured hooks directory but no hook-file mode. The second snapshot check at `E/native.py:206–207` has the same omission.

A chmod that removes execute permission from the ignored `.observation/hooks/commit-msg` file changes none of those recorded values. Git can then ignore the hook, so the runner may spend the accepted native episode without capturing its commit-msg opportunity. Post-run reconciliation would mark an unmatched commit unqualified, but that detects the lost observation after the task rather than refusing the changed preparation.

Smallest correction: include the installed hook's executable mode in the prepared fixture/equipment identity and verify it before native import and before task delivery. Keep the existing byte hash. Add a runner refusal test that changes only that mode and verifies no native task starts. This is a source-derived scenario, not an executed chmod test or observed native failure.

## Rechecked corrections

The runner now compares semantic Git state before native import and immediately before task delivery (`E/run.py:45–47`; `E/native.py:206–207`). The snapshot binds HEAD, branch, index tree, status, remotes, hooks path, signing, and author identity (`E/git_state.py:6–16`).

Named skill resource trees are re-enumerated and compared, so added files now cause drift refusal (`E/profile.py:69–78,113–120`). Loaded instruction paths are retained and compared before the task; the contract correctly identifies the prepared source list as a hypothesis that can cause refusal (`E/native.py:181–185`; `E/contract.md:31–35`). The global override filename is considered during preparation (`E/profile.py:103–106`).

Tool counting now uses explicit tool item kinds and distinct thread/item identities (`E/native.py:17–18,144–150`). Observer capture inventories every entry, retains missing/invalid record details, requires both named artifact identities, and makes any invalid observation disqualify the hook-context classification (`E/native.py:48–95`). It preserves candidate commit correspondences separately.

Preparation failures retain a receipt and partial root; native success and interruption paths both attempt final Git capture while preserving the primary error (`E/prepare.py:35–55`; `E/native.py:264–288`). History and text-input comparisons accept the supplied schema defaults (`E/native.py:237–245`).

## Protocol and interpretation limits

The initialization, thread-start, turn-start, skills discovery, MCP inventory, settings, model catalog, history response, and token-notification fields inspected agree with the supplied schemas. In particular, the MCP disabled state is a valid string enum, and token notifications preserve thread/turn identity with last and total breakdowns (`S/v2/ListMcpServerStatusResponse.json`, McpServerConnectionStatus; `S/v2/ThreadTokenUsageUpdatedNotification.json`, ThreadTokenUsage). This comparison establishes source/schema agreement, not successful native execution.

The synthetic protocol peer exercises the controller's external seam; it is not the Codex server or provider. The coordinator reports local seam tests passed. I read their cases but did not rerun them (`E/test_profile_run.py:129–187`; `E/test_preparation.py:15–57`; `E/test_run.py:41–83`; `E/test_observer.py:40–87`).

The metadata summary is explicitly superseded preparation and contains private-record identities, not the underlying instruction/profile content (`E/profile-evidence.json:2,15–42`). It cannot verify a future prepared profile; that needs fresh preparation and a concrete manifest.

Raw transport, unanswered control requests, histories, usage notifications, and capture errors remain distinct evidence. Missing native histories or unavailable child usage remain unknown; configured/requested child model fields do not establish per-turn execution telemetry. No token aggregation, money, quota, or removable-review claim is established here.

No native execution is accepted by this review. The preparation observes Git/native authoring and invokes neither the Jev service nor the jev-axi integration. It does not qualify semantic checker benefit, security efficacy, or a behavior assignment.
