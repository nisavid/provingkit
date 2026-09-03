# Provingkit

Provingkit is the public source repository for the six source members carried
by this cutover. Each member keeps its own identity and version, and the
current source-stage definition requires the complete six-member set.

The accepted Kit slate has a seven-member first release. Tidesmith enters
through the [tracked port](https://github.com/nisavid/provingkit/issues/25):
issue #25 after pull request #11. It is not part of this source stage or its
six-member definition.

## Members

Five of the six current source members are independently releasable Agent
Plugins:

- [`plugins/rolecasting/`](plugins/rolecasting/) contains **Rolecasting**, which
  plans model selection and delegation topology.
- [`plugins/tricritical/`](plugins/tricritical/) contains **Tricritical**, which
  coordinates independent review, adjudication, authorized
  revision, and fixed-point verification.
- [`plugins/versionkeeping/`](plugins/versionkeeping/) contains
  **Versionkeeping**, which owns safe Git checkpoints, publication planning,
  conflict resolution, worktree lifecycle, and fork synchronization.
- [`plugins/mergecraft/`](plugins/mergecraft/) contains **Mergecraft**, which
  owns pull-request authoring, publication, feedback, readiness, merge, and
  stack repair.
- [`plugins/artifact-customs/`](plugins/artifact-customs/) contains
  **Artifact Customs**, which assesses and maintains exact third-party software
  components under explicit policy.

**Task Witness** is the sixth member. It is a code-only validation package with
a manifest identity, not a portable Agent Plugin surface. Its current source
state is production-ineligible and supports source-stage validation only. See
the [Task Witness package reference](plugins/task-witness/README.md).

## Source and release boundary

[`release/provingkit/definition-v1.json`](release/provingkit/definition-v1.json)
is the versioned definition of the Kit. It names the exact member set and binds
each member to its own manifest. The repository contains a schema for a future
immutable release manifest, but it contains no release-manifest instance.

This repository is currently an unreleased source stage. It does not establish
a Provingkit version, tag, release, marketplace publication, installation, or
runtime qualification. The root
[`marketplace.json`](.claude-plugin/marketplace.json) is a source projection of
the five Agent Plugins; its presence is not marketplace publication.

The retained Linux and macOS Task Witness material under
[`qualification/historical/`](qualification/historical/) is historical input.
It is not current qualification evidence and does not make Task Witness
production-eligible.

The retained source-skill lineage manifest is also historical. It cannot
qualify this source stage; [issue #3](https://github.com/nisavid/provingkit/issues/3)
owns a fresh Provingkit rescout. Its mutation, receipt, and capture entrypoints
remain disabled until that rescout.

## Repository layout

- `plugins/` contains the six canonical member source trees and identity
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

Hindsight, Base Loadout, personal tools, and unrelated experiments are outside
this repository's source boundary.

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

An exit status of `0` confirms only the prepared source checks. Native
`public-release` and Task Witness qualification or final-release routes remain
unavailable. A later release must supply controls that this repository does
not own: an installed, host-owned, content-pinned, network-denied OS sandbox;
review authorization bound to the candidate bytes; opaque inherited handles
for private evidence; authenticated host and evaluation evidence with managed
signing-key custody and anti-replay state; and independent provider authority
bound to the exact candidate, policy, runtime, and endpoint. Until those gates
close, Task Witness remains `production_eligible: false`.

## Generated locks and review evidence

Do not hand-edit member content locks or generated projections. Change the
canonical source, run the owning validator's `--write-content-lock` mode where
one exists, inspect every generated change, and rerun the ordinary validator.
CI regenerates supported derived locks and requires a clean diff.

Task Witness is stricter: source-shape drift requires the independent review
named by its checked-in review contract. Its source-shape evidence has no
general-purpose writer and must not be rehashed as a mechanical lock update.

Preserve provenance when moving or deriving source. A reviewable change should
identify the source revision, explain retained historical or compatibility
references, and keep generated artifacts tied to the reviewed source bytes.
See [CONTRIBUTING.md](CONTRIBUTING.md) for the contribution contract.

## License

The repository license is MIT. Individual members may include their own
attribution or license files.
