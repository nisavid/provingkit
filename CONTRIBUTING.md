# Contributing to Provingkit

Contributions should leave the public source checkout reviewable, internally
consistent, and explicit about what their validation proves.

## Scope

Provingkit's members are Rolecasting, Tricritical, Versionkeeping, Mergecraft,
Artifact Customs, the code-only Task Witness package, and, once its port lands,
Tidesmith. Keep changes within those members, their shared validation, and the
Kit's repository contracts. Hindsight, Base Loadout, personal tools, and
unrelated experiments belong elsewhere.

Opening or merging a source change does not authorize a Provingkit release,
tag, release-manifest instance, marketplace publication, installation, or live
qualification. Propose those operations separately when their own policy and
authority exist.

## Prepare a change

1. Link the issue or decision that owns the change.
2. Update canonical source before any derived lock or projection.
3. Preserve each member's manifest identity and independent version boundary.
4. Use Conventional Commits for commit messages.
5. Run the focused commands under [Validate a source checkout](#validate-a-source-checkout)
   and report the checks that actually ran.

Do not present historical qualification inputs as current evidence. Files
under `qualification/historical/` are retained for provenance and design
review only.

## Validate a source checkout

Use CPython 3.13 or newer. Install the validation-only dependencies, then run
the Kit contract and each member's focused source-stage checks:

```sh
python -m pip install jsonschema==4.26.0 PyYAML==6.0.3

python -m unittest tests.test_validate_provingkit
python scripts/validate_provingkit.py .

python -m unittest tests.test_validate_rolecasting tests.test_rolecasting_eval_corpus
python scripts/validate_rolecasting.py .

python -m unittest tests.test_validate_tricritical tests.test_tricritical_eval_corpus
python scripts/validate_tricritical.py .

python -m unittest tests.test_validate_versionkeeping
python scripts/validate_versionkeeping.py .

python -m unittest tests.test_validate_mergecraft
python scripts/validate_mergecraft.py . --source-stage

python -m unittest tests.test_validate_artifact_customs tests.test_artifact_customs_eval_corpus
python scripts/validate_artifact_customs.py . --source-stage

repository="$(pwd -P)"
python -m unittest tests.test_task_witness_package
python scripts/validate_task_witness.py "$repository" --source-stage
```

These commands validate public source contracts. They do not grant release,
installation, runtime, or host-mutation authority.

### Prepared source-stage containment

The prepared wrapper exposes only `source-stage` validation. Invoke it from a
clean outer environment with an absolute, operator-qualified CPython 3.13+
executable and an absolute public candidate checkout:

```sh
/usr/bin/env -i LANG=C.UTF-8 LC_ALL=C.UTF-8 PATH=/usr/bin:/bin TZ=UTC /bin/sh \
  /absolute/path/to/public-provingkit/scripts/run_prepared_release_validation.sh \
  source-stage \
  /absolute/path/to/qualified/cpython \
  /absolute/path/to/public-provingkit
```

An exit status of `0` confirms only the prepared source checks; [What the source stage means](docs/release-boundary.md) explains what a release must add beyond them.

## Repository layout

- `plugins/` contains the canonical member source trees and identity
  manifests.
- `plugins/task-witness/` contains the code-only Task Witness package and its
  local manifest identity.
- `evals/` and `tests/` contain member behavior corpora and contract tests.
- `scripts/` contains source validators and controlled derived-artifact writers.
- `release/provingkit/` defines Kit membership and the future immutable
  release-manifest boundary.
- `release/plugin-content-locks/` contains generated content locks owned by
  member validators.
- `qualification/historical/` retains explicitly stale host-qualification
  inputs outside active CI discovery.

## Generated artifacts

The member validators own their content locks and generated projections. When
an owning validator supports `--write-content-lock`, run that mode after the
authored source is stable, review its complete diff, then run the ordinary
validator. Never edit a digest merely to make validation green.

Task Witness source-shape evidence is not an ordinary generated lock. Any
source-shape change must satisfy the independent review requirement recorded in
`release/task-witness/source-shape-review.json`; there is no mechanical
rebaseline command.

## Pull requests

A pull request should tell a reviewer:

- what behavior or source contract changes;
- which member or shared boundary owns it;
- which issue authorizes it;
- which source revision or retained history the change derives from, when
  provenance matters;
- which compatibility aliases or historical links remain and why; and
- which source-stage checks passed at the published revision.

Keep release and runtime claims no broader than the evidence. A green
source-stage check proves only the public source contract exercised by that
check.
