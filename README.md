# Provingkit

Provingkit is the public source repository for six coordinated Agent Plugins.
Each plugin keeps its own identity and version, and the current source-stage
definition requires the complete six-plugin set.

## Members

The current source members are independently releasable Agent Plugins:

- [`plugins/rolecasting/`](plugins/rolecasting/) contains **Rolecasting**, which
  plans model selection and delegation topology.
- [`plugins/tricritical/`](plugins/tricritical/) contains **Tricritical**, which
  coordinates independent review, adjudication, authorized
  revision, and fixed-point verification.
- [`plugins/versionkeeping/`](plugins/versionkeeping/) contains
  **Versionkeeping**, which owns safe Git checkpoints, publication planning,
  conflict resolution, worktree lifecycle, and fork synchronization.
- [`plugins/mergecraft/`](plugins/mergecraft/) contains **Mergecraft**, which
  owns exact human-facing GitHub body authoring plus pull-request publication,
  feedback, readiness, merge, and stack repair.
- [`plugins/artifact-customs/`](plugins/artifact-customs/) contains
  **Artifact Customs**, which assesses and maintains exact third-party software
  components under explicit policy.
- [`plugins/proseweaving/`](plugins/proseweaving/) contains **Proseweaving**, which holds
  portable standards and verification for agent-authored human-facing prose.

Task Witness is deferred optional equipment. It is not part of the preview
slate or a dependency of the ordinary plugins; see [issue #61](https://github.com/nisavid/provingkit/issues/61).

## Source and release boundary

[`release/provingkit/definition-v1.json`](release/provingkit/definition-v1.json)
is the versioned definition of the Kit. It names the exact member set and binds
each member to its own manifest. The repository contains a schema for a future
immutable release manifest, but it contains no release-manifest instance.

This repository is currently an unreleased source stage. It does not establish
a Provingkit version, tag, release, marketplace publication, installation, or
runtime qualification. The root
[`marketplace.json`](.claude-plugin/marketplace.json) is a source projection of
the six Agent Plugins; its presence is not marketplace publication.

Installable target projections are staged by the CI-only
[`release-artifact-projection`](docs/release-artifact-projection.md) process.
It excludes development material and emits a receipt bound to the source
commit, target, slate, inventory, and deterministic artifact digest.

The retained Linux and macOS Task Witness material under
[`qualification/historical/`](qualification/historical/) is historical input.
It is not current qualification evidence and does not make Task Witness
production-eligible.

The retained source-skill lineage manifest is also historical. It cannot
qualify this source stage; [issue #3](https://github.com/nisavid/provingkit/issues/3)
owns a fresh Provingkit rescout. Its mutation, receipt, and capture entrypoints
remain disabled until that rescout.

## Repository layout

- `plugins/` contains the six canonical plugin source trees and identity
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

Hindsight, Base Loadout, personal tools, and unrelated experiments are outside
this repository's source boundary.

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

When the prepared source checks pass, the wrapper prints the validated candidate
identities and exits with status `0`. It does not create a release receipt. Native
`public-release` and optional Task Witness qualification routes remain
unavailable. A later release must supply controls that this repository does
not own: an installed, host-owned, content-pinned, network-denied OS sandbox;
review authorization bound to the candidate bytes; opaque inherited handles
for private evidence; authenticated host and evaluation evidence with managed
signing-key custody and anti-replay state; and independent provider authority
bound to the exact candidate, policy, runtime, and endpoint. Until those gates
close, optional Task Witness equipment remains unavailable.

## Amberbridge

[Amberbridge](docs/amberbridge.md) is the release-evidence bridge between the
public Kit and its private deployment context. Its contracts and tests are
present; live release routes remain unavailable in this source stage.

## Generated locks and review evidence

Do not hand-edit member content locks or generated projections. Change the
canonical source, run the owning validator's `--write-content-lock` mode where
one exists, inspect every generated change, and rerun the ordinary validator.
CI regenerates supported derived locks and requires a clean diff.

Preserve provenance when moving or deriving source. A reviewable change should
identify the source revision, explain retained historical or compatibility
references, and keep generated artifacts tied to the reviewed source bytes.
See [CONTRIBUTING.md](CONTRIBUTING.md) for the contribution contract.

## License

The repository license is MIT. Individual members may include their own
attribution or license files.
