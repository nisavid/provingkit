# Evidence for supervision wording and injected failure behavior

This bundle preserves the six-cell Claude supervision-wording pilot, its
native file-tool preflight, and the separate offline failure-composition
comparison. It accompanies the September 26 research reports.

The executed scripts are retained byte-for-byte. JSON records are publication
projections: machine paths become `{scratch}`, `{jev-package}`, or
`{operator-home}`; encoded hook payloads are decoded, normalized, and encoded
again. Session event order, tool inputs/results, hook output, final responses,
file effects, and usage remain available. Opaque thinking signatures and
unrelated initialization metadata are omitted from stream projections.

`file-inventory.json` lists every bundle member other than itself, its public
SHA-256, and its original SHA-256 where applicable. Original hashes describe
the retained local records, not the normalized bytes. They are provenance
references, not a substitute for an independently trusted attestation.

## Contents

- `pilot-v2.py` and `pilot-hook.mjs`: executed six-cell instrumentation.
- `supervision-wording-preregistration.md`: outcomes and falsifiers declared
  before sessions; `supervision-pilot-execution-freeze.json` binds the manifest.
- `pilot/`: prepared manifest and six settings, hook logs, traces, summaries,
  and first-read markers. Each summary captures file bytes before reset.
- `native-preflight-v283.py` and `preflight/`: native file-tool observations and
  the coordinator's bounded qualification.
- `supervision-pilot-adjudication.json`: coordinator trace checks and manual
  classification of final responses and effects.
- `sys1-failure-composition.mjs`, its preregistration, and results: a separate
  closed-mock comparison. No proposed command executes and no real service
  request is made by that component experiment.

## Reproduction and reuse

Read the preregistration and scripts before use. The pilot runner is the
historical executed candidate, including exact pins to this preflight. It is
not a drop-in cross-host qualification tool: normalized records cannot pass
its original-byte checks. A new run needs a freshly observed native preflight,
a reviewed qualification record, updated artifact pins, and a new frozen
preregistration. Preserve the old evidence and retain failures instead of
reusing an existing run directory or retrying until success.

Keep model/tool capability checks, identical native controls across arms,
fresh sessions, the one-time post-read delivery rule, and raw-trace
adjudication. Verify delivered notes precede subsequent actions. Classify
questions separately from explanations and verify file bytes independently
of claimed completion. The fixture's source pins, local-route guard, and
exclusive records are checked at the tested layer; they are not a general
security boundary or deployment mechanism.

The preflight supports only the observed built-in file-tool controls. Its
symlink-write attempt failed on an earlier precondition. The wording pilot
uses one injected signal and one initial-message example per cell. The
offline failure comparison tests injected response paths, not real outages
or native permission outcomes. No live hook, production configuration, or
safety policy was changed by these experiments.

Jev-derived behavior is used under the MIT license retained alongside the
earlier [comparison evidence](../sys1-2026-09-26/README.md). The installed
package's source identities are in the manifest; no byte-identical upstream
build provenance is asserted.
