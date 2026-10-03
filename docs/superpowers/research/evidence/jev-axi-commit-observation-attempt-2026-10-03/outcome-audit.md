# First native attempt: outcome audit

The accepted launch stopped before task delivery because the CLI rejected the thread-start request. No developer authoring, message review, task commit, or hook-context opportunity was observed. The controller's retained failure label misidentifies the underlying error.

Anchors use `first-native-attempt/` for retained original source copies and `commit-observation-_osxwyau/` for episode artifacts.

## Observed sequence

`observer-execution-acceptance.json:3-8` records acceptance of one episode, source commit `73f0f2f2cfd71c69414bc0f7560d5c98575558d3`, manifest SHA-256 `d52e4a75fa3f444d345c45c5db4b586c5655c1f4b0a854b66700a27e7939e754`, and no automatic retries. The launch receipt references that same manifest and reports `native-incomplete` (`observer-launch-receipts/7c9f15df83a545558555b09b43056367.json:3-18`).

`commit-observation-_osxwyau/native-sent.jsonl:1-4` contains initialization, initialization acknowledgement, model listing, and thread-start requests. There is no `turn/start` request or delivered task prompt. The prepared prompt matches the retained `first-native-attempt/prompt.md` exactly, but preparation is not delivery.

`native-stdout.log:1-4` records CLI initialization and metadata notifications/model listing. Line 5 returns JSON-RPC error `-32600`: `thread/start.historyMode requires experimentalApi capability`. The sent initialization lacks that capability, while thread-start requests `historyMode: paginated` (`native-sent.jsonl:1,4`; original `native.py:115-117,174-180`).

## Concrete inconsistency

Original `first-native-attempt/native.py:181-185` handles response id 3 without first checking for an error/result. It substitutes an empty result and checks absent instruction sources against the prepared expectation. This produces `loaded instruction sources differ from prepared inventory`, recorded in `outcome.json:6` and the launch receipt.

That label is not evidence of actual instruction-source drift: thread-start failed before an instruction-source result existed. The native rejection should remain the primary explanation. The smallest source correction is to preserve and report RPC error responses before inspecting success fields, then reconcile the required capability against the actual CLI protocol. This audit authorizes neither that execution change nor another launch.

`native-process.json:2-7` reports all 9,628 received stdout bytes callback-consumed, no terminal success callback, and process exit code 0. The process exit does not establish observation success; the retained protocol error and incomplete receipt control the outcome. Stderr is empty.

## Git and interpretation

`git-evidence.json:2-20` records no post-baseline commits, no observer records, a clean status, and `git_boundary: unobserved`. All thirteen retained final application-file hashes match their prepared counterparts in `manifest.json:55-68`. This supports an unchanged retained application fixture; it is not an independent final snapshot of every Git/configuration property.

`outcome.json:2-12` has null thread/turn, empty histories/settings, no tools or child dispatches, and no usage events. Together with the rejected request and absent task delivery, this is a protocol/setup failure before an authoring episode, not a native task-quality failure, review absence finding, permission stop, or Jev/jev-axi efficacy observation.

Missing usage establishes no zero-cost claim. Setup, CLI metadata/protocol activity, retained failure, and audit effort remain research costs; billing, quota, and model usage are unknown here (`first-native-attempt/contract.md:112-119`). Native permissions, installed skill delivery, and review behavior were not qualified.

All thirteen frozen input hashes matched before and after this read-only audit. The decisive `native-stdout.log` SHA-256 is `7a5afa04e3236bdde6b080b94ce07f05f25feda601de78a91fa5e8bc10e57167`. No writes, source execution, native tasks, external calls, or delegation occurred.
