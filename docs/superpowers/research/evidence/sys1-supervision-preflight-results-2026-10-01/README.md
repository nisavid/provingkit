# Passive native preflight results

This packet preserves the admitted observations and costs of four accepted passive attempts, including one controller-censored attempt. Read the [joined report](../../2026-10-01-jev-axi-passive-native-preflight.md) for the claim limits and remaining qualification.

- `attempts.json` contains selected native counters, receipt timings, captured-event counts, and the repeated Stop-ID example. It omits transcript bodies and replaces fixture paths in that example with `<project>`.
- `retained-record-identities.json` binds all 183 original private record files. Keys use relative batch and coordination aliases; digests still identify the unmodified private bytes. The records include inherited host context and are not included here.
- `artifact-checks.json` records the independent parser CLI checks and read-only report artifact checks. The censored Codex report is checked only against its last delivered requirement.
- `inspection-reviews.json` identifies the independent context and accounting inspections and their joined disposition.
- `candidate-repair.patch` applies to `native-supervision/` in the [original source packet](../sys1-supervision-preflight-2026-09-30/README.md). It corrects receipt identity and adds one regression. Apply the zero-context patch with `git apply --unidiff-zero candidate-repair.patch` from that packet root. Restore that packet's pinned integration build/dependencies as documented before running its local tests. The old executed source remains unchanged.
- `local-repair-checks.json` distinguishes the local red/green check, eight-check pass, and retained-message replay from native qualification. Replay still rejects the old incomplete report episode. No new native episode has run with this correction.

The packet's identity file covers these published files; it is distinct from the private-record identity list. Local publication review is recorded separately from the two native-result inspections. No result authorizes live configuration changes or upstream publication.
