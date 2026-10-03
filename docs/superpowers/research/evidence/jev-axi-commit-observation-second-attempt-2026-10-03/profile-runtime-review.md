DONE

The profile correction passes this bounded source and metadata review. I found no concrete defect requiring another source change.

In `jev-axi-commit-observation-2026-10-02/profile.py`, the invocation disables `cua_repl` under `unified-computer-use@openai-bundled` and `fork-ops` under `fork-ops@fork-ops` through per-plugin server policies. Plugin enablement remains available for skill discovery. These bindings cover the observed installed profile; they are not a general policy for future plugins.

Preparation requires a complete, unpaginated connector inventory, empty tools, and runtime states that are unavailable or disabled. That distinction matches `ListMcpServerStatusResponse.json`: runtime status describes a thread connection and may be null when unavailable. The corrected metadata transcript contains twelve servers with null states and empty tool inventories. Its sent requests are initialization, skill discovery, and connector discovery; there is no thread or turn start. The profile records 179 skill entries and explicitly leaves thread-runtime disablement unqualified. The manifest binds that profile and retains `execution_authorized: false`.

The stronger task-delivery check remains intact in `native.py`: it queries the actual thread and requires every connector to report disabled with empty tools before sending `turn/start`. Accepting null states during preparation does not weaken that check.

The synthetic CLI peer in `test_profile_run.py` derives plugin behavior from the invocation overrides and distinguishes metadata discovery from thread discovery. Its success paths exercise the null-state preparation case and the later disabled-state gate. The unexpected-connector regression checks refusal, a retained preparation receipt, no runnable manifest, and no task delivery. I reviewed these tests without executing them; the nineteen passing local checks are coordinator-reported.

The retained preparation failure correctly preserves the earlier false refusal on null states. The public `jev-axi-commit-observation-second-attempt-2026-10-03/README.md` and failure projection keep metadata preparation separate from the second accepted launch, its connected plugin servers, and unmeasured startup costs. A second factual and prose pass found no necessary wording correction.

All 26 frozen input hashes matched before and after review. No files were changed and no workload, native task, or external call was run. Native compatibility and commit-authoring behavior remain unqualified. Another episode requires separate acceptance of the reviewed source and concrete manifest digest.
