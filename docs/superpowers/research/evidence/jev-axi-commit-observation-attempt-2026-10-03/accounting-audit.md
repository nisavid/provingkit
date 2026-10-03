DONE_WITH_CONCERNS

# First native attempt accounting audit

The accepted attempt reached CLI initialization and model discovery, then failed at thread creation before task delivery. It supplies no commit-authoring or semantic-review observation. All 13 frozen input digests matched before and after this read-only audit using `research`; no source, tests, native tasks, or external calls were executed.

Anchors below use retained artifact filenames and `first-native-attempt/` for the frozen original-source copies. The audit is bound to `observer-result-accounting-dispatch.json` and accepted manifest SHA-256 `d52e4a75fa3f444d345c45c5db4b586c5655c1f4b0a854b66700a27e7939e754`.

## Observed sequence and inconsistency

`observer-execution-acceptance.json:3–8` records acceptance of one episode at source commit `73f0f2f2cfd71c69414bc0f7560d5c98575558d3`, with automatic retries disabled. The launch receipt retains that same manifest digest and reports `native-incomplete`, not an observed task.

`native-sent.jsonl:1–4` retains initialize, initialized, model/list, and thread/start with paginated history. It contains no turn/start or task prompt. `native-stdout.log:5` returns error -32600: `thread/start.historyMode requires experimentalApi capability`. There is no successful thread-start response.

The recorded primary reason is inconsistent with that protocol result: `outcome.json:6` and launch receipt line 17 say loaded instruction sources differed. In `first-native-attempt/native.py:181–185`, an error response becomes an empty result and reaches the instruction-source check without first requiring success. Thus the retained reason describes an inventory mismatch that was never evaluated against a successful thread response. The source also initializes without the capability requested by the actual error (`first-native-attempt/native.py:115–117,174–180`). Preserve both facts; the original attempt cannot be recast as an instruction inventory observation.

Smallest correction for a separately reviewed candidate: declare the required experimental capability during initialization and reject/report protocol error envelopes before interpreting response fields. This audit authorizes no rerun.

## Duration, retention, and cost limits

The launch receipt spans 15:31:33.501260 to 15:31:34.345289 UTC on 2026-10-03: **0.844029 seconds** by subtraction (`7c9f15df83a545558555b09b43056367.json:4,18`). This is the recorded controller interval, including initialization, refusal, shutdown, and final capture; it is neither model latency nor whole-workflow duration.

`native-process.json:2–7` records 9,628 received and callback-consumed stdout bytes, below the 2 MiB cap, exit code 0, and no successful terminal callback offset. The stderr input is empty, verified by its frozen empty-file digest. A process exit code of zero does not override the protocol error or incomplete controller result.

`outcome.json:2–12` has no thread, turn, children, histories, tools, or usage. These agree with the absence of task delivery in the sent stream. They establish no observed model task turn or provider token endpoint; they do **not** establish zero tokens, zero billing, or zero quota consumption.

`git-evidence.json:2,18–20` retains no commits or observer invocations, an unobserved Git boundary, and clean status. Every retained final application-file digest matches its manifest initial-file digest. No committed change or replaceable review step was observed.

Preparation, metadata discovery, local tests, coordinator investigation, this audit, recovery, operator effort, and any provider-side metadata accounting are outside this launch interval or unmeasured by these inputs. Their costs remain separate unknown components. Parent/child aggregation has no measured endpoints here. The record supports no economic comparison.

The contract requires retained attempts and no automatic retry (`first-native-attempt/contract.md:69–80,112–119`). These frozen artifacts establish one retained launch, not a complete inventory of unrelated activity. Neither Jev-service usage nor jev-axi assessment usage is evidenced by this attempt.
