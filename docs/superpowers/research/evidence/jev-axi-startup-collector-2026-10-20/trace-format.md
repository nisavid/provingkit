# Trace projection and supported input

The stream preserves observed operands and outcomes without reconstructing
paths or inferring the cause of startup failure. The current binding is
`strace-source-subset/v1`: a synthetic, source-informed input subset, not an
attestation of any installed tracer's output.

## Supported shapes

Complete `open`, `openat`, and `openat2` calls have a decimal successful return
or `-1 ERRNO (message)`. The projection retains the errno and drops the human
message. Paths retain decoded bytes as lowercase hexadecimal; no UTF-8
decoding or canonical path resolution occurs. Plain printable ASCII, C named
escapes, hexadecimal byte escapes, and octal byte escapes are supported.
Pointer, truncated, malformed, and NUL-containing path representations are
incomplete inputs.

`open` and `openat` retain symbolic open flags and an optional octal mode.
`openat` also retains the numeric dirfd or `AT_FDCWD`, without supplying an
unobserved directory history. `openat2` accepts a structure with required
`flags` and `resolve`, optional `mode`, and a decimal size. Unknown structure
fields, pointer fallbacks, and numeric unknown flag bits remain unsupported.

Unprefixed records belong to the supplied root identity. The documented
`[pid N]` prefix is accepted only when it matches that root. Other identities
are refused. An unfinished selected call emits a begin record; its matching
resume emits an end record with the same call identity and both receipt
positions. A mismatched, duplicate, or missing completion is incomplete.
Receipt order is not cross-thread causality.

`+++ exited with N +++` records an observed root exit. It is separate from the
collector's observed direct-child return code. Raw EOF after that record can
complete this restricted stream, but `descendant_closure` remains `unknown`.
EOF, a signal sent by the collector, a tracer exit, or an exit request never
establishes that all descendants exited.

The remaining selected syscall families, signal/restart messages, additional
identities, output-file PID prefixes, timestamps, and unrecognized text are
unsupported. They terminate the projection with an incomplete record rather
than disappearing from the evidence. The 46-operation selection in the
startup proposal is unchanged; this decoder does not yet cover it. Extending
coverage and qualifying a real backend are required before the diagnostic.

## Framing and bounds

The adapter emits header, operation, identity, and terminal records. Each has
a receipt sequence and collector-monotonic observation timestamp. The header
names the binding and marks backend execution unqualified. Operation records
name their lifetime and call and identify their raw line receipts. Results
and operands use typed states; numeric values remain decimal strings.

Raw reads and assembled lines are at most 4,096 bytes, with 4 MiB total raw
input. Normalized records are at most 4,096 bytes including LF; total output
is at most 4 MiB and 16,384 records. One record and 4,096 bytes are reserved
for the terminal. `--max-records` and `--max-bytes` can lower those two output
bounds, to no less than two records and 8,192 bytes respectively. Header and
terminal count toward every output bound. Overflow retains only the accepted
prefix and terminal, never a truncated success record.

The terminal reports raw bytes consumed and output counts before itself.
It records incomplete framing, unsupported shapes, bounds, and unknown
identity closure explicitly. The rejected raw payload is not retained.
This field-selection behavior is tested with synthetic records; it is not
a confidentiality guarantee for real tracing.

## Primary source basis

All source references below use strace v7.2 commit
`195ac8ddbf6fad16ff1ff125b0feb725b6c46dcf`:

- The [manual](https://github.com/strace/strace/blob/195ac8ddbf6fad16ff1ff125b0feb725b6c46dcf/doc/strace.1.in)
  gives open/error examples, unfinished/resumed correlation, lifecycle
  spelling, and string-escaping options. Its string limit does not bound
  filenames; the adapter imposes its own raw-line bound.
- [The open decoders](https://github.com/strace/strace/blob/195ac8ddbf6fad16ff1ff125b0feb725b6c46dcf/src/open.c)
  establish dirfd/path/flag/mode order and `openat2`'s structure and size.
  [The openat tests](https://github.com/strace/strace/blob/195ac8ddbf6fad16ff1ff125b0feb725b6c46dcf/tests/openat.c)
  and [openat2 tests](https://github.com/strace/strace/blob/195ac8ddbf6fad16ff1ff125b0feb725b6c46dcf/tests/openat2.c)
  contain expected-output constructions. These tests were read, not run.
- [String quotation source](https://github.com/strace/strace/blob/195ac8ddbf6fad16ff1ff125b0feb725b6c46dcf/src/util.c)
  supplies the byte-escaping implementation used to interpret the source
  examples. Synthetic adapter checks do not establish actual option delivery,
  personality, PID presentation, or behavior of a future installed binary.

The local test inputs are worked examples derived from those interfaces.
They are not retained traces from Codex or from a real strace invocation.
