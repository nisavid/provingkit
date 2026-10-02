# Frozen reader and hook investigation inputs

The [reconciled findings](../2026-10-02-reader-hook-findings.md) give the current
conclusions. This archive preserves earlier source reports and the first
prototype so the cross-examination is reproducible. Reports describe what was
known at their stage; unresolved source questions in a first report may be
answered in its supplement. The first prototype has known mismatches corrected
in the [current prototype](../../prototypes/receiver-evidence/README.md).

| Stage | Fixture identity / executor | Runtime producers |
| --- | --- | --- |
| Independent first findings | [Report](identity-first.md) | [Report](state-first.md) |
| Independent public engine inspection | [Supplement](identity-engine.md) | [Supplement](state-engine.md) |
| Exchange of frozen tracks and prototype | [Cross-examination](identity-cross.md) | [Cross-examination](state-cross.md) |

`prototype-first/` contains the exact first code, contract, tests, findings,
and manifest supplied for cross-examination. Its tests describe invented input;
passing them did not establish the native origin schema. The researchers found
that mismatch through source inspection and counterexamples.

`manifest.json` hashes the preserved inputs, including the nested prototype
manifest. The coordinator copied report bytes without rewriting them and checked
their SHA-256 identities. The optional digest footer on the identity
cross-examination identifies its payload separately from the complete report.
These are ordinary coordinator-retained native worker results, not portable
attestations of model identity or enforced worker permissions.

The current prototype resolves the native-origin and meta-record mismatch,
retains the checked receiver/request binding, and describes normalized Stop
text and receipt-time limits. The current report incorporates the engine
getter semantics. Initial findings and cross-examination remain here as
historical evidence, not instructions or adopted live procedure.
