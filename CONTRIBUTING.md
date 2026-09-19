# Contributing to Provingkit

Contributions should leave the public source checkout reviewable, internally
consistent, and explicit about what their validation proves.

## Scope

Current changes stay within the seven Agent Plugins: Rolecasting, Tricritical,
Versionkeeping, Mergecraft, Artifact Customs, Proseweaving, and Praxis. Task
Witness is shelved optional equipment; its historical records remain available
for future reassessment.
Hindsight, Base Loadout, personal tools, and unrelated experiments belong
elsewhere.

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
python -m pip install idna==3.18 jsonschema==4.26.0 PyYAML==6.0.3

python -m unittest tests.test_validate_provingkit
python scripts/validate_provingkit.py .

python -m unittest tests.test_validate_rolecasting tests.test_rolecasting_eval_corpus
python scripts/validate_rolecasting.py .

python -m unittest tests.test_validate_tricritical tests.test_tricritical_eval_corpus tests.plugins.test_tricritical_review_evidence
python scripts/validate_tricritical.py .

python -m unittest tests.test_validate_versionkeeping
python scripts/validate_versionkeeping.py .

python -m unittest tests.test_validate_mergecraft
python scripts/validate_mergecraft.py . --source-stage

python -m unittest tests.test_validate_artifact_customs tests.test_artifact_customs_eval_corpus
python scripts/validate_artifact_customs.py . --source-stage

python -m unittest tests.test_validate_proseweaving
python scripts/validate_proseweaving.py .

python -m unittest tests.test_validate_praxis
python -m unittest tests.test_aeon_bell tests.test_aeon_bell_codex_status tests.test_aeon_bell_binding
python scripts/validate_praxis.py .
```

These commands validate public source contracts. They do not grant release,
installation, runtime, or host-mutation authority. The Praxis check binds the
[member's governed inputs](plugins/praxis/README.md#validation) to
`release/plugin-content-locks/praxis.json`; it does not run the Aeon Bell engine
or assert runtime behavior. The three `tests.test_aeon_bell*` modules exercise
the engine, status adapter, and structured harness binding against constructed
fixtures. Binding conformance uses Node.js 24.21.0 as a test runner; installed
monitor operation uses the harness’s JavaScript runtime.

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

When the prepared source checks pass, the wrapper prints the validated candidate
identities and exits with status `0`. It does not create a release receipt.
The [release boundary](docs/release-boundary.md#source-checks-and-release-evidence)
explains the additional controls required for release and live qualification.

## Repository layout

- `plugins/` contains the seven canonical plugin source trees and identity
  manifests.
- `evals/` and `tests/` contain member behavior corpora and contract tests.
- `scripts/` contains source validators and controlled derived-artifact writers.
- `release/artifact-projection-policy-v1.json` defines the allowlisted runtime
  files for each supported marketplace target.
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
validator. Never edit a digest merely to make validation green. CI regenerates
supported derived locks and requires a clean diff. Praxis writes only
`release/plugin-content-locks/praxis.json`. Its
[member validation contract](plugins/praxis/README.md#validation) names the
complete input inventory and the supported regeneration command.

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
