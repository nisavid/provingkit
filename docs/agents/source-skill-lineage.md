# Retained source-lineage maintenance

Use this procedure when changing `scripts/validate_source_skill_lineage.py`,
`scripts/refresh_source_skill_lineage.py`, their recovery moves, or the active
tests in `tests/test_validate_source_skill_lineage.py`.

## Boundaries

The retained evidence describes `nisavid/agents` candidate
`8ec465ea915c6759a3693ac8515f0ee3901b8a4f`. Its source manifest has SHA-256
`838b6ef68103f2139ebc9728b7ad93ddc5db52dd90e92ac2293cde2a47d55896`
and five package records: Artifact Customs, Mergecraft, Rolecasting,
Tricritical, and Versionkeeping. Keep `RETAINED_DISTRIBUTIONS` aligned with
those records. Current Provingkit membership is a separate six-plugin Slate
that also includes Proseweaving.

Provingkit maintainers own these entrypoints and this procedure. Issue #3
exclusively owns a future Provingkit rescout. Preserve the historical manifest,
missing Task Witness roots, absent manager-registry state, and skipped
historical suites as evidence limits. The first public diagnostic is currently
`candidate package aggregate drift`; it does not establish that downstream
source-inventory, contribution, or host bindings are clean.

## Source contract

Every public reader mode acquires the shared lineage lock within the fixed
materialization limit, including `--receipt-summary` with either the live root
or an explicit artifacts root. Internal no-lock validation accepts only an
explicitly materialized snapshot while its caller holds the repository lock.
On deadline expiry, reject admission, release any late-acquired lock, and emit
the pathless lock-limit diagnostic.

The refresher pins the validator's byte size and SHA-256. Update both values
whenever the validator changes. Keep directory and non-directory recovery
moves on `_move_bound_noreplace()` with typed binding callbacks. Public
`write()` tests must reach the directory path and both non-directory quarantine
paths. Exercise destination appearance, binding substitution, applied partial
failure, first-error precedence, and preserved source, occupant, and retained
state with inert temporary fixtures. Mock only issue #3's rescout gate.

## Validation

Run the active source-lineage tests, then exercise both retained readers:

```sh
python -m unittest tests.test_validate_source_skill_lineage
python scripts/validate_source_skill_lineage.py .
python scripts/refresh_source_skill_lineage.py check .
```

The two readers currently exit 1 with `candidate package aggregate drift` and
leave retained evidence unchanged. Run the current-source stage only through
the prepared wrapper with operator-qualified absolute paths:

```sh
/bin/sh "$PWD/scripts/run_prepared_release_validation.sh" source-stage "$QUALIFIED_PYTHON" "$PWD"
```

That stage intentionally excludes retained lineage. Direct invocation of
`validate_public_release.py` is unsupported.

Record the reviewed source revision, validator size and SHA-256, commands and
results, intentional skips, and any unavailable platform check. A consumer may
use this procedure only when those results cover the same source revision and
its evidence dependencies.
