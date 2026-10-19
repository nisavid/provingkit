# Prepared preservation-response fixtures

`prepared-admission-schema.json` is an unchanged public-source fixture from
[`release/host-preservation-admission/record.schema.json` at `c7116240650551cf20946a45e25410d134a013ab`](https://github.com/nisavid/provingkit/blob/c7116240650551cf20946a45e25410d134a013ab/release/host-preservation-admission/record.schema.json).
Its SHA-256 is `42a5e0213de0a877b88edeb686be3905313349898b7d1168ebe86cf2f16480c6`.
`constructed-complete-record.json` is unchanged constructed test data from
[`tests/fixtures/host_preservation_admission/constructed-record.json` at the same revision](https://github.com/nisavid/provingkit/blob/c7116240650551cf20946a45e25410d134a013ab/tests/fixtures/host_preservation_admission/constructed-record.json).
Its SHA-256 is `cdb79fe1d2f66d2e1535705da98d1dbac860b2c470a012e32540d4613a8bff36`.
The CLI cases bind its request, contract, and raw subject/baseline records to
constructed local files. Its other identities remain shape-only placeholders;
the fixture supplies no owner admission, complete semantic correspondence, or
host observation.
