# Select one bounded publication record

This invocation uses manual selection and the unchanged [evidence importer](../jev-axi-passive-observation-2026-10-05/import_records.py). The supported interface is its command-line invocation and resulting evidence package. It is a preservation tool, not a relevance selector or security filter. The [source-route research](../jev-axi-collection-routes-2026-10-05/README.md) and [accounting research](../jev-axi-collection-routes-2026-10-05/usage-and-accounting.md) supply the known limits.

## Admission and reads

1. After acceptance, verify candidate hashes and the private source binding. Record acceptance time, monotonic start, source device/inode/size, and the last complete line-feed boundary. Read at most 64 KiB from the source prefix to identify the matching session and available producer metadata, and at most 1 MiB at the end to locate the boundary. Failure to establish the thread identity or boundary ends collection. Retain the admission delay; records before the boundary are antecedents, and a boundary-crossing record is not proved prospective.
2. Read at most 8 MiB immediately before the fixed boundary using seek and a fixed byte count. Discard a leading partial line when the read begins mid-record. Identify the current publication request and relevant amendments, using the privately listed accepted-decision records as explicitly identified coordinator records where original messages are missing. Those records do not become original human message bytes. Retain missing origin, referents, or context.
3. At the terminal condition, recheck source identity and perform one read of at most 8 MiB after the boundary. Source replacement, excess append size, missing content, timestamps in disagreement, incomplete final lines, or unjoined operations limit the result. No polling, resumption, replacement source, or additional chat read follows.
4. Acquire only specifically bound ordinary artifacts and selected Git-object/diff output, charging all repeated acquisition against their shared 4 MiB ceiling. Prefer already retained exact bytes. Do not reconstruct a missing historical check by running it again. An artifact produced after the terminal boundary may report an earlier ordinary operation, but its creation and acquisition times must remain distinguishable from that operation.

## Selection and preservation

Parse complete lines in memory and keep only visible current requests/amendments, relevant commentary/final reports, associated calls/results, and measurement records needed for the stated consumers. Exclude reasoning, system/developer messages, world-state/configuration records, and unrelated private material. A wrapper carrying excluded material is not retained whole. A necessary transformed excerpt is a separately marked derivative, never an exact source span.

Consider top-level `token_usage_record` as well as supported event wrappers. The prior procedure's narrower `event_msg` selection missed the reported shape. Unknown fields/wrappers remain unidentified; do not make them conform by inference. Source-defined response usage and turn/thread cumulative fields overlap. Preserve each occurrence with source offset/digest and available response, turn, thread, session, and root-turn identities. Byte-identical duplicate content alone does not prove duplicate events.

Create the explicit manifest with original source path, absolute byte offset, length, SHA-256, meaningful label, and `bytes` or `jsonl` format. Retain selection reasons, omissions, read traffic, fragments, temporal boundaries, and unknown correspondences. Selected spans must fit the importer limits and the invocation's acquisition budget. Count importer rereads and manifest reading as collection traffic, even when the same bytes were already read.

Run the pinned importer once with the manifest and a new directory. Preserve the exact manifest, imported bytes, index where available, receipt, exit, and tool duration. Exit 0 proves selected-span import/index success only; exit 2 is partial, and exit 1 or a missing receipt is incomplete. Do not overwrite or automatically retry an attempt.

## Interpretation and whole-workflow costs

Join a verification occurrence to its actual checked candidate, source dependencies, command, output, and result. Present missing historical identities as unavailable. A final commit, current file read, or owner report cannot supply them retrospectively. Join ordinary publication artifacts to their exact intended/observed ref and range. A quiet transport does not prove hook assessment or delivery.

Usage arithmetic needs a qualified producer definition, stable lineage, known baselines/endpoints, and resolved duplicate identities. Otherwise retain source-reported counters without totals. Resume/fork inheritance, synthetic context-window estimates, missing usage, cache reuse, and failed attempts remain distinct. No child source is included; parent records cannot establish complete child cost. Requested model selection is not effective-model attestation.

| Cost component | Route or retained gap |
| --- | --- |
| Research, setup, maintenance, and refresh | Existing preparation/dispatch/review records; untimed activity and model usage remain unknown |
| Retrieval, selection, packing, and interpretation | Byte/read accounting, observed collection calls, importer timing, and explicitly labeled active-effort estimates; elapsed intervals are not active effort |
| Worker, child, ambient model, and Jev attempts | Eligible source records and ordinary attempt/result identities; missing/failed usage and excluded child histories remain unknown; this observation adds no Jev call |
| Downstream verification, retries, interruption, and recovery | Actual retained calls/results and ordinary terminal outcomes, including non-action; unrecorded work stays unknown |
| Operator checking or genuine resumption | Optional voluntary record only after ordinary work; absence is unknown effort |
| Measurement burden | Collection actions, interpreter/import work, and voluntary-record burden, kept separate from ordinary task work |
| Latency, money, and quota | Measured elapsed components with their scope; no attributable billing or quota route is established, and list-price estimates are not either |

Keep setup/maintenance separate from recurring work; assume no amortization. Charge matching shared production once and retain standalone/marginal scope without inferring counterfactual savings. The resulting description can support a later hypothesis, not a winning behavior assignment.
