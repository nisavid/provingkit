# Corrected native attempt: outcome audit

The corrected launch created an idle Codex thread and passed its instruction-source and skill-inventory checks, then stopped because two MCP servers were connected outside the accepted disabled-connector profile. No task prompt was sent, so no commit-authoring or separate-review observation exists.

Anchors use `second-native-attempt/` for frozen source copies and episode artifact filenames for `commit-observation-3lowv2rr/`.

## Progress actually observed

`observer-second-execution-acceptance.json:3-9` records one accepted episode, source commit `9c813973f721f14923ee9ca73be387a5c819356d`, manifest SHA-256 `0db25cdfcc4c1c7232b3996425b34382fbeef27a23fa159e5943c230df7cd110`, and no automatic retry.

`native-sent.jsonl:1-6` contains initialization with `experimentalApi: true`, acknowledgement, model listing, thread-start, skill discovery, and connector-status discovery. Unlike the first attempt, `native-stdout.log:5-6` records successful creation of an idle thread with no turns, Sol at medium effort, and CLI version 0.160.0.

The successful thread response reports the expected global `AGENTS.md` instruction source, `on-request` approvals with the user reviewer, and workspace-write permissions with network and shared temporary-directory access disabled. The retained instruction-source artifact agrees with the prepared expectation.

`native-stdout.log:9` returns one error-free skill-discovery row containing 179 entries. The controller's exact inventory comparison passed: it subsequently sent connector discovery (`native-sent.jsonl:6`; `second-native-attempt/native.py:186-205`). This verifies the prepared entrypoint inventory at that boundary, not skill invocation, instruction comprehension, or model behavior.

## Actual stop and smallest discrepancy

`native-stdout.log:12` returns an unpaginated connector inventory: ten servers are disabled with no tools, but `cua_repl` is connected with three tools and `fork-ops` is connected with fourteen. Startup notifications show both reaching ready (`:7-8,10-11`).

The controller's `active connector outside the profile` error is accurate (`outcome.json:6`; launch receipt `c09c2dcd4b2e4cf582103266f3bb12d0.json:17`). Its connector guard stopped before profile recheck, final pre-delivery Git recheck, or `turn/start` (`second-native-attempt/native.py:206-218`). There is no RPC rejection or instruction-source mismatch in this attempt.

The source discrepancy is the incomplete connector-disabling route: `second-native-attempt/profile.py:31-49` enables plugins and disables individual MCP names only from the loaded config's `mcp_servers` section. The retained native command supplies no individual disable setting for the two connected names. The observed runtime inventory therefore disproves the assumption that those overrides disable every exposed server. These inputs do not independently establish each server's origin.

The smallest correction needs to account for the missing runtime connector sources while preserving installed authoring skill discovery and the existing all-disabled guard. No specific replacement command, executed remediation, or third-launch authority is established by this audit.

## Outcome and limits

`git-evidence.json:2-20` reports no new commits, no observer records, clean status, and an unobserved Git boundary. All thirteen retained final application-file hashes match the manifest's initial counterparts. `outcome.json:2-12` contains a thread but no turn, histories, tools, children, or usage events.

This is a setup/profile qualification stop before task execution, not a developer failure, review-absence result, or Jev-service/jev-axi efficacy result. Thread-start permission reporting passed; turn-time permissions and behavior remain unobserved. Connected tools were exposed, but no tool invocation is evidenced.

Absent usage does not establish zero tokens, billing, quota, or whole-workflow cost. Original attempts remain separate retained research work.

All seventeen frozen input hashes matched before and after review. The decisive stdout SHA-256 is `11acd35da1dd550cb44ee0be538224d30568415ea6dc13b055533868a7219300`. No writes, source execution, native tasks, external calls, or delegation occurred.
