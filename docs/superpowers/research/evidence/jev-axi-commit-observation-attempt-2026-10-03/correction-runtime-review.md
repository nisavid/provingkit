DONE

# Protocol correction runtime review

No concrete consequential defect was found in the reviewed correction. All 19 frozen input digests in `observer-correction-runtime-dispatch.json` matched before and after this bounded read-only review using `research`. I read the complete corrected controller and relevant runner/tests; no source, tests, native tasks, provider calls, or writes were performed.

Paths use `E/` for `docs/superpowers/research/evidence/jev-axi-commit-observation-2026-10-02/` and `A/` for `docs/superpowers/research/evidence/jev-axi-commit-observation-attempt-2026-10-03/`.

## Corrected behavior

`E/native.py:115–118` declares `capabilities.experimentalApi: true` during initialization. The supplied CLI protocol schema defines that boolean as opting into experimental methods/fields (`v1/InitializeParams.json:25–31,68–77`). This directly addresses the retained paginated-history rejection (`A/first-attempt.json:6–12`).

`E/native.py:128–136` retains response error envelopes in an exclusive-create artifact and raises a primary exception containing response ID and serialized error before any result-field checks. Thus a thread-start RPC rejection no longer becomes an absent-instruction mismatch. Incoming permission/user-input requests still take their earlier unanswered-stop path.

The outer controller retains the primary exception, attempts final Git capture, and preserves a capture error separately (`E/native.py:269–293`). The public runner records native-incomplete for a controller exception and returns a nonzero result (`E/run.py:52–62`). Existing manifest/source/fixture checks, hook-mode identity, and one-attempt reservation/refusal remain intact (`E/run.py:28–51`; `E/git_state.py:14–21`).

The synthetic peer now requires the declared capability for thread-start. Its success case therefore exercises capability delivery, while a separate forced rejection checks the exact error is retained, task delivery does not occur, and instruction drift is not invented (`E/test_profile_run.py:28–43,186–202`). The coordinator reports eighteen local checks passed after red/green regressions; I did not rerun them. These tests exercise the external runner seam, not the real server or model.

## Evidence and authority limits

The public attempt projection preserves the original RPC rejection separately from the controller's misleading label, with request counts, duration, and private artifact identities (`A/first-attempt.json:2–35,36–80`). It agrees with the retained outcome/accounting audits. It neither changes the original attempt nor supplies a successful native observation.

The contract states capability negotiation and error preservation directly (`E/contract.md:85–95`). Source/schema agreement is a clean bounded preparation pass. A second real episode has not been observed by this review, and the first acceptance supplies no automatic retry. Fresh preparation and separate execution acceptance remain necessary (`A/README.md:50–51`).

Native task delivery, loaded profile agreement, model execution, usage semantics, cost, and commit-authoring/review behavior remain unqualified. This correction invokes neither the Jev service nor the jev-axi assessment integration and establishes no checker benefit or behavior assignment.
