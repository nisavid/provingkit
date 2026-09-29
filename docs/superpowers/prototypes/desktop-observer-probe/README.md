# Prepare a disposable Desktop observer probe

This candidate provides an offline Desktop patch, a bounded observer, strict
sample readers, and a procedure for one disposable Code task. It prepares
[the observer probe](https://github.com/nisavid/provingkit/issues/278).
Installation and live observation require the reviewed revision named by the
separate [probe authorization](https://github.com/nisavid/provingkit/issues/279).

## Start here

- [Probe procedure](probe-procedure.md): fixture, exact setup prompt, collection,
  application changes, restoration, retention, and cleanup boundary.
- [Authorization checklist](authorization-checklist.md): concrete scopes to
  accept or amend before execution.
- [Application operation](application-operation.md): host preflight, receipt
  comparison, protected backup, candidate staging, launch validation,
  restoration, and exact private cleanup.
- [Published build receipt](candidate-build.json): retained source copy of the
  generated build receipt. The candidate archive and generated
  `build-receipt.json` remain in private local staging.
- [Packaging evidence](packaging-evidence.md) and
  [process-binding evidence](process-binding-evidence.md): inspected
  dependencies and the limits of those observations.
- [Procedure capture](procedure-capture.md): current consumer instructions and
  proposed maintained ownership after the experiment.

The accepted input is the
[observer prototype](../desktop-runtime-observer/README.md) at
`be9abcb2714231eb1f10d5586361dc9d15361ca0`. This preparation implements its
selected receiver projection and concrete insertion points, with bounded
collection and exclusive file publication. Every observation remains partial
and unqualified. No notification, delivery, or acknowledgment is tested here.

## Source layout

| File | Responsibility |
| --- | --- |
| `observer-contract.mjs` | Shared schema names, binding and selected-report constants, limits, and named observation gaps |
| `observer-probe.mjs` | Exact binding, explicit arm, bounded getter calls, projection, and sample export |
| `desktop-adapter.mjs` | Selected manager view, generation/mode hooks, bootstrap, and collection lifecycle |
| `manager-patch.json` | Exact source replacements for the inspected manager |
| `probe-reader.mjs` | Strict schema, binding, interval, and sequence checks over sample bytes |
| `read-probe-file.mjs` | Acquisition of one explicitly selected private sample file |
| `selected-executor-linux-identity.mjs` | Fresh sample acquisition followed by bounded observation of its selected Code PID |
| `selected-executor-linux-identity-internal.mjs` | Process acquisition with a synthetic I/O seam |
| `archive.mjs`, `build-candidate.mjs` | Offline source patching, CommonJS bundling, and ASAR construction |
| `verify-archive.mjs` | Independent extraction and complete member comparison |

The Linux helper performs no reads on import and is never called by the app
sidecar. Its future invocation needs explicit process-data scope. App process
identity, retained query reports, and OS observations stay separate; none
authenticates the query-to-OS association.

Freshness is accepted only when wall time and Linux monotonic elapsed time both
remain within the selected maximum age. The producer binds monotonic values to
the Linux boot ID, and the explicitly invoked Linux acquirer must observe the
same boot ID before it can use a sample for process reads. A rollback, future
timestamp, expiry, or incomparable boot rejects the sample first.

The boot-domain check reads the nonsecret
`/proc/sys/kernel/random/boot_id` path. The Desktop producer reads it while
creating the bound probe, and the Linux helper reads it only during an
explicitly selected acquisition. Any later live grant must include that path.

## Reproduce source checks

Use Node.js with the independently installed `@electron/asar 4.3.0` reader and
`esbuild 0.28.2`. Set `PROBE_ASAR_READER` to the file URL of the former's
`lib/asar.js`, and `PROBE_ESBUILD` to the latter's `lib/main.js`. Run from the
repository root:

    node --test --test-timeout=25000 docs/superpowers/prototypes/desktop-observer-probe/*.test.mjs docs/superpowers/prototypes/desktop-runtime-observer/*.test.mjs
    git diff --check

The build takes an explicitly supplied pristine archive and a new output
directory. It never imports or executes Desktop code:

    node docs/superpowers/prototypes/desktop-observer-probe/build-candidate.mjs "$PRISTINE_ASAR" "$NEW_OUTPUT_DIRECTORY"
    node docs/superpowers/prototypes/desktop-observer-probe/verify-archive.mjs "$PRISTINE_ASAR" "$NEW_OUTPUT_DIRECTORY/candidate.asar" "$NEW_OUTPUT_DIRECTORY/desktopRuntimeObserver.js" "$NEW_OUTPUT_DIRECTORY/manager.js"
    node --check "$NEW_OUTPUT_DIRECTORY/manager.js"
    node --check "$NEW_OUTPUT_DIRECTORY/desktopRuntimeObserver.js"

The independent archive comparison must cover all 365 candidate members. It
permits only the manager change and sidecar addition; the other 363 original
members must retain their bytes and metadata. Extraction and syntax checks do
not establish that the modified app loads.

`build-candidate.mjs` writes `build-receipt.json` beside the candidate archive.
That generated receipt is the output record tied to those archive bytes. After
the complete archive comparison and both syntax checks succeed, retain its
exact bytes as the published source receipt:

    cp -- "$NEW_OUTPUT_DIRECTORY/build-receipt.json" docs/superpowers/prototypes/desktop-observer-probe/candidate-build.json
    cmp -s -- "$NEW_OUTPUT_DIRECTORY/build-receipt.json" docs/superpowers/prototypes/desktop-observer-probe/candidate-build.json

Then rerun the source tests and `git diff --check` on the final source revision.
Any subsequent source change requires a new build, complete archive
verification, syntax checks, retained receipt, and final review. The generated
and published receipts must compare byte for byte again before authorization
and before staging.

## Review boundary

[Security design guidance](security-design.md) retains the original bounded
Daybreak design response verbatim, SHA-256
`2b9e00f54d283beb46a9197dd5e2b098fa6b1b2e45afe9c1673194c6b25d6267`.
It is historical design input; the current source and procedure define the
candidate under review. Source controls were developed through tools-disabled
Daybreak sessions using approved source packets and synthetic results. The
requested route was `gpt-daybreak-blue-latest` through Codex CLI `0.159.0`.
No product-owned model-execution attestation is available.

The selected application route is temporary installed-archive exchange during
one scheduled window in the current signed-in profile. It includes one
candidate launch and one restored launch, with Desktop shut down before each
exchange. The current candidate bundles the adapter, observer, and shared
contract; complete offline verification covered all 365 candidate members, left
363 original members unchanged, and included syntax checks of the manager and
sidecar. Runtime loading remains unverified, and the latest source must be
rebuilt before final review.

Getter effects, runtime account, model, permission and cwd semantics, full
permissions coverage, and native address binding remain live questions. No app
installation, launch, private receiver read, task creation, setup prompt,
cleanup action, or notification was performed during this preparation.
