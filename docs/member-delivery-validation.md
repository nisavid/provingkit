# Offline member-delivery validation

`scripts/validate_member_delivery.py` checks the prepared nonpassing preservation-response branch against a caller's frozen input identities. It always returns a nonpassing result: complete observations, actual admission, delivery artifacts, and the hosted caller still require implementation and qualification under the [member-delivery design](superpowers/specs/2026-10-06-repository-configuration-alpha/member-delivery-validation.md).

## Invocation and input

Run Python with `jsonschema` available; the source workflow supplies version `4.26.0`. An unavailable dependency produces an incomplete result. Timestamp checking is implemented separately and does not depend on optional schema-format packages.

```sh
python scripts/validate_member_delivery.py --request request.json --inputs inputs --output result.json
```

The request uses `schema_version: provingkit-member-delivery-request-v1` and a `preservation` object with exactly these fields:

| Field | Value |
| --- | --- |
| `response` | Logical name of the raw response. |
| `admission_request` | Logical name of the immutable request to which the response must bind. |
| `reviewed_contract` | Logical name of the independently selected contract bytes. |
| `schema` | Logical name of the prepared schema bytes. |
| `inputs` | Map from logical name to `{ "path": "relative/path", "bytes": 123, "sha256": "64 lowercase hex digits" }`. |
| `expected_dependencies` | Map from each expected dependency name to `missing` or `unavailable`. |

The four roles must be distinct and present in the input map. Paths resolve beneath `--inputs`. Use stable, cooperatively maintained local files. The response supplies identities, not paths or retrieval instructions. This interface performs no network retrieval.

The supported [prepared schema](https://github.com/nisavid/provingkit/blob/c7116240650551cf20946a45e25410d134a013ab/release/host-preservation-admission/record.schema.json) has SHA-256 `42a5e0213de0a877b88edeb686be3905313349898b7d1168ebe86cf2f16480c6`. Supply those exact bytes. The [producer contract](https://github.com/nisavid/provingkit/blob/c7116240650551cf20946a45e25410d134a013ab/docs/host-preservation-admission.md) defines both response branches. A complete observation can pass shape checking here, but its semantics remain unimplemented and its result stays incomplete.

The validator also carries those unchanged schema bytes in `scripts/member_delivery_prepared.schema.json` and checks their identity before use. Available evidence is checked for contradictions even when another input cannot be opened. An unavailable caller file remains explicit missing evidence; it cannot suppress a detectable response contradiction.

## Checks and results

The consumer checks raw byte counts and hashes, the closed response shape, request and contract bindings, the complete known-record identity set, and the caller's expected dependency states. Known records must name every mapped input except the response itself, including expected files that cannot be opened. Dependency names cannot repeat, and at least one dependency state must match the declared missing/unavailable outcome. A mixed set preserves both states; this interface invents no precedence between them.

Strict UTF-8 JSON decoding rejects duplicate keys, non-JSON numeric constants, malformed content, and requests beyond the parser's nesting limit. Observation timestamps require a calendar date, time, and explicit RFC 3339 offset. Leap-second labels are checked against the UTC day boundary; no external leap-second announcement table or clock-currentness check is performed. Available input bytes are reread before reporting a consistent nonpassing response. These are cooperative observations, with no atomic snapshot guarantee.

| Exit | Result | Meaning |
| --- | --- | --- |
| `1` | `rejected` | A supported input is malformed or contradicts an expected identity, binding, or dependency state. |
| `2` | `incomplete` | The response is consistently nonpassing, required files or a dependency are unavailable, or the requested validation is unimplemented. |

`preservation_response`, when present, preserves the supplied origin, missing/unavailable outcome, claim, timestamp, dependencies, and reason. `established_claims` is always empty. `owner-reported` is a supplied label: ordinary hashes and the caller's input map do not authenticate an owner or establish acceptance. The caller must obtain expected identities independently; candidate-supplied expectations cannot admit that candidate.

Run the owning CLI cases with `python -m unittest tests.test_validate_member_delivery`. They use constructed requests and responses plus an unchanged public schema fixture. They establish this nonpassing slice's behavior, not host preservation, installation acceptance, or a working Actions caller.
