# Bounded startup collection: synthetic implementation

This equipment preserves a startup specification, collects one initialize
exchange, and joins it with a bounded trace projection. Its current consumer
is the disposable local test driver for the
[startup proposal](../jev-axi-runtime-metadata-proposal-2026-10-20/proposal.md).
Real tracing and Codex startup remain unqualified and require separately
accepted execution contracts.

## Local verification

From the repository root:

```sh
python -m unittest discover \
  -s docs/superpowers/research/evidence/jev-axi-startup-collector-2026-10-20 \
  -p 'test_*.py'
```

The tests use disposable Python and shell processes and literal synthetic
trace records. They exercise the preparation and run CLIs, saved evidence,
and the trace stream interface. They start no Codex, tracer, or provider call.
The forked-process test covers cooperative group shutdown after the direct
child exits; it does not establish closure of an arbitrary descendant tree.

## Preparation and run interfaces

`startup_collector.py prepare --spec SPEC --output NEW_DIRECTORY` preserves
the supplied JSON specification and records identities for the collector,
adapter, executable, and declared source files. Existing destinations are
refused. Source bodies are not copied. Each preparation record is at most
64 KiB. The specification contains:

- `schema: 1`, an absolute executable in a command vector, an absolute `cwd`,
  and absolute `sources` paths;
- `expected_initialize`, containing exactly the string fields `userAgent`,
  `codexHome`, `platformFamily`, and `platformOs`;
- optional lower `limits`: `pipe_bytes` (at most 2 MiB), `message_bytes`
  (256 KiB), `startup_seconds` (30), `term_seconds` (5), and `kill_seconds` (5);
- optional `trace: {"binding":"strace-source-subset/v1"}`, paired with a
  `{trace_fd}` placeholder in the command vector. The run substitutes an
  inherited write descriptor. This is exercised only by fake servers.

`startup_collector.py run --package PACKAGE --output NEW_DIRECTORY` rechecks
the recorded identities, preserves the specification and manifest, and
executes the command with the inherited environment and permission boundary.
It sends only the proposal's initialize request: no `initialized` notification
or second request. The attempt retains the sent request, selected metadata,
byte counts, pipe EOF observations, direct-child return code, and outcome.
If tracing is selected, `trace.jsonl` and its digest are retained too.

The outcome is compact UTF-8 JSON, limited to 96 KiB. Its four metadata
strings must exactly match those already admitted in the 64 KiB specification;
their compact encoding cannot exceed that source representation. The remaining
fixed fields, including the bounded trace summary, use less than 2 KiB. Escaped
lone surrogates remain JSON escapes. Together, the preserved specification
(64 KiB), manifest (64 KiB), outcome (96 KiB), and fixed initialize request
(under 1 KiB) stay below the proposal's 256 KiB control-record ceiling. The
separately bounded trace stream is not part of that ceiling.

If an outcome nevertheless exceeds its bound, the collector retains a smaller
terminal record with the metadata omitted, the original outcome's digest, and
`reason: outcome_projection_limit`. The observed reason, byte counts, direct
child return code, and EOF observations remain available; the CLI reports
failure. With the current admitted schema, the bound above prevents this
fallback from being reached.

A response that first arrives during shutdown cannot turn a timeout into
success. Malformed, mismatched, unsolicited, or oversized replies are
incomplete outcomes. Unsupported trace input prevents a successful attempt
even when the initialize metadata is valid. Failed attempts remain in their
new directories; the CLI never reuses an existing result directory.

Exit code 0 identifies the implemented exchange and projection conditions.
It does not certify the full diagnostic. Every launched attempt records
`diagnostic_qualification: not_established` and
`descendant_closure: unknown`. The implementation does not qualify permission
enforcement, confidentiality, historical failure causation, or an actual
tracer's completeness.

## Trace stream

`trace_adapter.py --root-pid PID` reads bytes from stdin and emits normalized
JSONL to stdout. The run CLI consumes the same adapter in process. The
standalone stream caller owns its input deadline; the run CLI supplies the
startup and shutdown windows. See [trace-format.md](trace-format.md) for
supported shapes, primary sources, bounds, and explicit gaps.

## Consumer handoff

Before preparing a real diagnostic, load this procedure at its reviewed
revision and verify the local checks on unchanged source. Expand and qualify
the raw decoder for the proposal's selected operations, qualify the actual
binary/options/output route with disposable tracees, and reconcile descendant
identity and closure. Then join those results with the runtime profile and
whole-envelope accounting in a reviewed execution contract. Neither this
synthetic implementation nor a clean source review releases those gates.
