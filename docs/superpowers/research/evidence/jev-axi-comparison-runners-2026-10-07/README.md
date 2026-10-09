# Exercise claim and coverage request mechanics

These research CLIs prepare frozen inputs and retain request, response, outcome, and accounting evidence for the [ordinary comparison contracts](https://github.com/nisavid/provingkit/issues/467). This checkpoint implements local HTTP mechanics. Live transport, complete consumer access, final cases, and execution acceptance remain separate work.

From this directory, run the public-interface checks:

```sh
python -m unittest test_comparison_runner
```

The tests start a controlled local HTTP service and invoke the preparation and execution CLIs with disposable inputs. Their supplied responses exercise parsing and evidence handling; they establish no model accuracy, workflow benefit, live endpoint compatibility, or economic advantage.

## Preparation and execution

`comparison_runner.py prepare --spec INPUT.json --output NEW_DIRECTORY` validates a specification, preserves its input files, and emits a manifest path and SHA-256. The manifest binds the runner, source specification, cases, conditions, limits, and schedule. Existing output directories are refused.

`comparison_runner.py run --prepared PREPARED_DIRECTORY --manifest-sha256 DIGEST --output NEW_DIRECTORY --local-http` verifies the prepared identities and runs the frozen schedule against loopback HTTP endpoints. Every configured endpoint must be supported before any request starts. Without `--local-http`, the current implementation refuses execution because live transport is unfinished.

The claim kind shapes requests for Jev, Decisions, and Responses around the same four-way evidence question. The coverage kind supports Responses tool continuations over supplied source records. It retains unavailable sources explicitly. Preparation does not validate a live provider's behavior or grant permission for an experiment.

Coverage defaults to `mode: comparison`, requiring exactly one ordinary and one deterministic arm for every model/effort profile. Profiles stay together; the first arm alternates with the case and profile ordinal. An explicit `mode: diagnostic` supports individual mechanical probes and is identified in both manifest and run summary. A diagnostic run supplies no paired comparison result.

Coverage packets without a `version` retain the version-1 schema and behavior. Version 2 uses exactly `version`, `task`, `common_context`, `relationship_summary`, `sources`, and `comparisons`. Both arms receive the complete `common_context`, identical source and comparison catalogs, and identical evidence functions. The deterministic arm adds only `relationship_summary`.

Each version-2 source has `id`, `snapshot`, and a repository-relative `path`, plus either complete UTF-8 `content` and its `sha256`, or `unavailable_reason`. A snapshot is either `{"kind": "git_commit", "object_id": "<immutable Git object ID>"}` or `{"kind": "candidate_fileset", "manifest_sha256": "<SHA-256 of the frozen file-set manifest>"}`. Candidate file sets retain their own identity even when derived from historical Git content. Acquisition owns the correspondence between the frozen manifest, snapshot paths, and supplied bytes; this runner validates and preserves supplied identities and content digests without accessing Git.

A comparison has `id`, `base`, `head`, `inventory`, and `patch`; its endpoints use the same snapshot descriptors. Each view contains complete `content` with its `sha256`, or an explicit `unavailable_reason`. `evidence.read_source(source)` returns a complete source record, `evidence.source_identity(source)` returns its identity and available content byte count, and `evidence.inspect_comparison(comparison, view)` returns the complete `inventory` or `patch` view with its endpoints. Calls accept only catalog IDs and exact argument keys. Unknown IDs, duplicate argument keys, unsupported functions, and unsupported views produce `tool_error`.

Version 2 retains each serialized function-result envelope in a `.body` file with its digest and measured byte count. Tool bounds and delivery accounting include that complete envelope, including JSON escaping, and repeated submissions count again. Request records measure the actual retained request body. A result exceeding a bound stops the cell as `resource_incomplete`; no source or comparison view is shortened to fit. Version-1 tool-byte accounting retains its existing inner-output basis.

## Evidence and accounting

Each attempted request has a verbatim body file and a recorded digest, alongside its structured reservation and attempt record. Raw response bodies and supported events remain available, including bounded partial responses. Coverage preserves prepared tool results that were never submitted and counts repeated submission of earlier results separately. Recorded submission attempts do not establish provider receipt or consumption.

Cell-local refusals, incomplete or malformed outputs, timeouts, response limits, and resource limits remain outcomes while later independent coverage cases continue. A model mismatch or accounting error stops its affected condition. The claim protocol retains its separate stopping behavior. Unattempted slots and unavailable cases remain visible.

The [comparison design](../jev-axi-comparison-producers-2026-10-07/comparison-design.md) defines endpoint-specific accounting. Jev and Decisions accept input-only rate specifications; nonzero cache, write, or output rate components are refused. Responses values the reported input/cache/write/output partitions and keeps missing or inconsistent usage explicit. Raw token counters remain evidence even when a particular counter has no charge. API-rate equivalents, confirmed charges, and subscription quota are different quantities. These CLIs do not measure complete workflow cost.

Run summaries bind the prepared manifest digest and a unique run ID. Schedule slots,
request reservations, attempts, and coverage-cell summaries retain the same run and
slot IDs; every request also has its own attempt ID. Attempt intervals begin before
reservation and end after answer interpretation and usage valuation. UTC start/end
points support ordering; monotonic start/end points, duration, and first-byte latency
support timing within that invocation. First-byte latency is null when unobserved.

`usage_scope: per_request` identifies usage from a supported response envelope;
missing or non-object usage has unknown scope. This describes the retained endpoint
contract, not provider receipt or billing confirmation. Token subtotals retain every
reported nonnegative integer, including failed requests, and separately count missing
and invalid counters. `unreported_attempts` is their combined count. Counter validity
here concerns the raw counter's shape; inconsistent partitions still invalidate
valuation. Unknown and invalid valuations remain separate counts, and any unvalued
attempt keeps the complete API-rate equivalent unknown. Reasoning-token subtotals
are evidence only and are never added to output tokens for valuation.

`workflow-evidence.json` is a separate run-linked record for preparation, grading,
operator effort, billing, subscription usage, and complete workflow measurements.
The runner leaves these unknown, with null values and no evidence. A downstream
measurement must identify its status as observed, estimated, or unknown and cite its
evidence; request estimates do not fill these fields or define quota conversions.

## Consumer handoff

Use this equipment through the project-local `handling-sys1-incidents` [comparison contract](../../../../../.agents/skills/handling-sys1-incidents/references/comparison-contract.md). Its next consumer must bind the reviewed runner and producer revisions, independently prepared ordinary sources, matched tools, evaluator separation, exact routes and prices, grading, bounds, and stopping rules in a reviewed execution contract. Experimental execution still requires its accepted concrete contract.

The [claim fixtures](fixtures/claims/README.md) contain controlled assertions, including deliberately unsupported or false statements. Their construction metadata belongs to preparation and evaluation, outside model input.
