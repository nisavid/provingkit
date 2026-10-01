DONE, no findings.

The revised preflight has a clean bounded accounting/source pass for frozen binding `3aebb81c33e96a16d13d695e602ea773665582051f1c9d46d951d86ff9c6b777`.

All 25 frozen inputs, 353 manifest-bound runtime source files, eight settings/configuration files, and five dependency resolutions matched before and after review. The 18 prepared project files also matched their manifest hashes at the final check. The current batch’s private attempt directories contain no records.

Citation prefix `C/` means this evidence directory. The reviewed `ordinary-native-preflight-contract.md` is published as `contract.md`.

- Unique launch receipts precede manifest validation, lock acquisition, and reservation creation. They preserve launch intervals, expected digest, exit, error, and launcher output while keeping prior reservations intact. Missing receipt storage and interrupted receipts have explicit reconciliation limits. (`C/native-supervision/run.py:25–61,64–107`; `C/ordinary-native-preflight-contract.md:46`)
- The contract accurately scopes output retention per transport process and distinguishes Claude tool-use counting from Codex command/file-change item counting. It includes additional records and in-flight overshoot, and makes no hard billing, token, host, or disk guarantee. (`C/ordinary-native-preflight-contract.md:40`)
- Both Codex temporary-write exclusions are requested and required in reported policies. The contract distinguishes configuration verification from runtime containment and read-access qualification. (`C/native-supervision/native_controller.py:291–304,352–375`; `C/native-supervision/native_support.py:28–50`; `C/ordinary-native-preflight-contract.md:36`)
- Passive captures publish atomically and signal failure through nonzero exit plus an attempted marker. Before another turn, the controller checks lifecycle completion, captured-record validity, aggregate event counts, and Stop coverage. The contract correctly limits this to aggregate agreement rather than an individual native/capture identity join. (`C/native-supervision/passive_hook.py:15–23,73–87`; `C/native-supervision/hook_receipts.py:21–84`; `C/native-supervision/native_controller.py:245–252,439–447`; `C/ordinary-native-preflight-contract.md:26`)
- Costs include native work, instrumentation, setup, review, failures, diagnosis, and operator effort. Unknown usage remains unknown; cumulative counters, overlapping intervals, tokens, billing, and constrained quota remain distinct. The later reconciliation and comparison acceptance remain separate gates. (`C/ordinary-native-preflight-contract.md:62–66`)

I performed read/hash inspection only. The retained local checks are synthetic evidence; I did not rerun them. This pass establishes no native admission, containment outcome, provider-route attestation, supervision benefit, comparison acceptance, or rollout authority.
