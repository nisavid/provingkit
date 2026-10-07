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

## Evidence and accounting

Each attempted request has a verbatim body file and a recorded digest, alongside its structured reservation and attempt record. Raw response bodies and supported events remain available, including bounded partial responses. Coverage preserves prepared tool results that were never submitted and counts repeated submission of earlier results separately. Recorded submission attempts do not establish provider receipt or consumption.

Cell-local refusals, incomplete or malformed outputs, timeouts, response limits, and resource limits remain outcomes while later independent coverage cases continue. A model mismatch or accounting error stops its affected condition. The claim protocol retains its separate stopping behavior. Unattempted slots and unavailable cases remain visible.

The [comparison design](../jev-axi-comparison-producers-2026-10-07/comparison-design.md) defines endpoint-specific accounting. Jev and Decisions accept input-only rate specifications; nonzero cache, write, or output rate components are refused. Responses values the reported input/cache/write/output partitions and keeps missing or inconsistent usage explicit. Raw token counters remain evidence even when a particular counter has no charge. API-rate equivalents, confirmed charges, and subscription quota are different quantities. These CLIs do not measure complete workflow cost.

## Consumer handoff

Use this equipment through the project-local `handling-sys1-incidents` [comparison contract](../../../../../.agents/skills/handling-sys1-incidents/references/comparison-contract.md). Its next consumer must bind the reviewed runner and producer revisions, independently prepared ordinary sources, matched tools, evaluator separation, exact routes and prices, grading, bounds, and stopping rules in a reviewed execution contract. Experimental execution still requires its accepted concrete contract.

The [claim fixtures](fixtures/claims/README.md) contain controlled assertions, including deliberately unsupported or false statements. Their construction metadata belongs to preparation and evaluation, outside model input.
