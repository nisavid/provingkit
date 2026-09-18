# YAML/frontmatter migration qualification inputs

This candidate exposes the accepted production file-identity interface while
retaining every existing CLI test. It supplies a concrete source revision for
[the bounded migration qualification](https://github.com/nisavid/provingkit/issues/134).
The test-placement proposal and its qualification remain pending.

## Accepted contract and first scope

The [adoption decision](https://github.com/nisavid/provingkit/issues/133#issuecomment-5734052041)
selects `contains_historical_identity(relative_path: Path, original_content:
bytes) -> bool` in `scripts/validate_provingkit.py`. It composes the existing
path-specific transformation, format/frontmatter extraction, normalization,
and detection. Detection and repository allowance are separate decisions;
existing `ValidationError` diagnostics propagate. The scanner retains discovery,
symlinks, allowlist checks, original-byte hashing, and CLI behavior.

The first qualification cohort is fixed to these existing methods:

| Method in `tests/test_validate_provingkit.py` | Cases |
| --- | ---: |
| `test_yaml_semantic_escapes_for_legacy_repository_identity_are_rejected` | 3 |
| `test_legitimate_yaml_semantics_remain_accepted` | 3 |
| `test_yaml_frontmatter_bom_does_not_change_identity_detection` | 4 |
| `test_legitimate_bom_frontmatter_remains_accepted` | 2 |

Every original input and file-level assertion stays. Qualification must account
for every existing CLI assertion, select and justify retained integration checks,
and report the exact proposed change in CLI executions. Other identity tests keep
their current execution paths. This candidate replaces zero CLI executions.

## Source and procedure inputs

The fresh production baseline is
`91af898ef72fce984a4843071e9fbf33cf878113`. Its validator and original test file
match the accepted prototype base
`ad31344cdcb9891438cf1e92c27c776945bee6ab` byte for byte. Other production inputs
have changed, so the separately running scheduling benchmark cannot establish
this candidate's performance.

The interface composition and ordinary examples come from the
[reviewed prototype](https://github.com/nisavid/provingkit/blob/5f266ed701501e4b9fb3b08d3c72558947244271/docs/superpowers/research/2026-09-18-file-identity-prototype.md)
at `5f266ed701501e4b9fb3b08d3c72558947244271`. That reproduction procedure is the
consumed source. The
[accepted case inventory](https://github.com/nisavid/provingkit/blob/1494a78f2025544db0511c2909344973331d07e7/docs/superpowers/research/2026-09-18-file-identity-cases.json)
records the original assertions and surrounding integration obligations.

With the validation dependencies from `.github/workflows/provingkit-source.yml`,
the ordinary interface observations run with:

```sh
python -m unittest -v tests.test_file_identity_interface
```

These six examples observe the public interface's ordinary results and error
context. They establish no migrated coverage, adversarial equivalence, allowlist
equivalence, or CI savings. The unchanged complete original suite and owning
source validation remain required candidate checks:

```sh
python -m unittest tests.test_validate_provingkit
python scripts/validate_provingkit.py .
git diff --check
```

## Qualification still required

The judgment that a proposed test placement preserves adversarial and
allowlist/composition acceptance must use the applicable route selected through
`choosing-agent-models`. Freeze the final proposal and its evidence before that
review. Ordinary observations do not replace the required judgment.

The completed proposal needs fresh baseline and candidate identities, complete
original and proposed suite results, owning validation, actual production-call
evidence with original bytes, and independent reviews current on the same
candidate. Capture the qualified comparison procedure through
`capturing-agent-procedures` and connect its reviewed result to the eventual
production-adoption consumer.

The performance gate is repeatable complete-suite CI elapsed savings, with
runner time and variation reported. Use matched dependencies, retained history,
runner conditions, and fixed scheduling. Direct-call timing does not meet this
gate. Coordinate all hosted allocations with the preview orchestrator. This
throwaway candidate supplies no production landing or hosted-run clearance.
