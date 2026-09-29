# Prepare a disposable Desktop observer probe

This candidate provides an offline Desktop patch, a bounded observer, strict
sample readers, and a procedure for one disposable Code task. It prepares
[the observer probe](https://github.com/nisavid/provingkit/issues/278).
Installation and live observation require the reviewed revision named by the
separate [probe authorization](https://github.com/nisavid/provingkit/issues/279).

## Start here

- [Probe procedure](probe-procedure.md): fixture, exact setup prompt, collection,
  application changes, and restoration.
- [Authorization checklist](authorization-checklist.md): concrete scopes to
  accept or amend before execution.
- [Application operation](application-operation.md): host preflight, protected
  backup, candidate staging, launch, restoration, and cleanup.
- [Build receipt](candidate-build.json): source and output digests for the
  copied archive. The archive itself stays in local staging.
- [Packaging evidence](packaging-evidence.md) and
  [process-binding evidence](process-binding-evidence.md): inspected dependencies
  and the limits of those observations.
- [Procedure capture](procedure-capture.md): current consumer instructions and
  proposed maintained ownership after the experiment.

The accepted input is the [observer prototype](../desktop-runtime-observer/README.md)
at `be9abcb2714231eb1f10d5586361dc9d15361ca0`. This preparation implements its
selected receiver projection and concrete insertion points, with bounded
collection and exclusive file publication. Every observation remains partial
and unqualified. No notification, delivery, or acknowledgment is tested here.

## Source layout

| File | Responsibility |
| --- | --- |
| `observer-contract.mjs` | Shared schema names, binding keys, limits, and named observation gaps |
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

## Reproduce source checks

Use Node.js with the independently installed `@electron/asar 4.3.0` reader and
`esbuild 0.28.2`. Set `PROBE_ASAR_READER` to the file URL of the former's
`lib/asar.js`, and `PROBE_ESBUILD` to the latter's `lib/main.js`. Run from the
repository root:

    node --test --test-timeout=15000 docs/superpowers/prototypes/desktop-observer-probe/*.test.mjs docs/superpowers/prototypes/desktop-runtime-observer/*.test.mjs
    git diff --check

The build takes an explicitly supplied pristine archive and a new output
directory. It never imports or executes Desktop code:

    node docs/superpowers/prototypes/desktop-observer-probe/build-candidate.mjs "$PRISTINE_ASAR" "$NEW_OUTPUT_DIRECTORY"
    node docs/superpowers/prototypes/desktop-observer-probe/verify-archive.mjs "$PRISTINE_ASAR" "$NEW_OUTPUT_DIRECTORY/candidate.asar" "$NEW_OUTPUT_DIRECTORY/desktopRuntimeObserver.js" "$NEW_OUTPUT_DIRECTORY/manager.js"
    node --check "$NEW_OUTPUT_DIRECTORY/manager.js"
    node --check "$NEW_OUTPUT_DIRECTORY/desktopRuntimeObserver.js"

The independent archive comparison permits only the manager change and sidecar
addition. The other 363 original members must retain their bytes and metadata.
Extraction and syntax checks do not establish that the modified app loads.

## Review boundary

[Security design guidance](security-design.md) retains the original bounded
Daybreak design response verbatim, SHA-256
`2b9e00f54d283beb46a9197dd5e2b098fa6b1b2e45afe9c1673194c6b25d6267`.
It is historical design input; the current source and procedure define the
candidate under review. Source controls were developed through tools-disabled
Daybreak sessions using approved source packets and synthetic results. The
requested route was `gpt-daybreak-blue-latest` through Codex CLI `0.159.0`.
No product-owned model-execution attestation is available.

The procedure proposes one scheduled window in the current signed-in profile,
with temporary installed-archive replacement and two shutdown/launch cycles.
Getter effects, candidate loading, runtime account,
model, permission and cwd semantics, full permissions coverage, and native
address binding remain live questions. No app installation, launch, private
receiver read, task creation, setup prompt, or notification was performed during
this preparation.
