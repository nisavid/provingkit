# Developing Artifact Customs

This page is for people who contribute to Artifact Customs, fork it, or work
with its internals. It stays in the source repository and is not part of an
installed copy. The [README](README.md) is the page for people using the
plugin.

## Layout

```text
plugins/artifact-customs/
├── plugin.json                  # Canonical Agent Plugins v1 manifest
├── .claude-plugin/plugin.json   # Claude adapter manifest
├── references/                  # Authored shared contracts
├── skills/                      # Three public skills and their local projections
├── topology.json                # Component, call, and authority map
├── README.md                    # Front page for people using the plugin
├── DEVELOPING.md                # This page
├── CHANGELOG.md
└── LICENSE
```

Claude Code uses the `.claude-plugin/plugin.json` identity projection. Each
skill's `references/` directory carries ordinary local projections of the
package-level `references/` contracts it reads. Release validation requires
every projection to match its single authored package-level source byte for
byte.

The release projection copies only an allowlisted subset of this tree into
each target's installable plugin tree. Every target leaves out
`topology.json` and this page. Only the `claude` target carries
`.claude-plugin/plugin.json`, and only the `agent-plugins` target carries
`skills/*/agents/openai.yaml`. The
[release artifact projection](https://github.com/nisavid/provingkit/blob/main/docs/release-artifact-projection.md)
document describes the policy and the builder.

## Validation

Development evals, fixtures, tests, and generated content locks live in the
repository-level `evals/`, `tests/`, and `release/` trees rather than this
runtime plugin root. The behavior corpus and its fixtures are at
`evals/artifact-customs/`.

From the repository root, run:

```sh
python3 scripts/validate_artifact_customs.py .
python3 -m unittest tests/test_validate_artifact_customs.py
python3 -m unittest tests/test_artifact_customs_eval_corpus.py
python3 -m unittest tests/test_artifact_customs_behavior_eval.py
```

The validator pins the plugin root inventory, including this page, and checks
the manifests, topology, skill contracts, shared-contract projections, and the
content lock. The lock,
`release/plugin-content-locks/artifact-customs.json`, records the digest of
every regular file in the plugin root. Its SHA-256 is bound as Artifact
Customs' content identity in `release/provingkit/definition-v1.json`. After
editing canonical source, regenerate the lock with
`python3 scripts/validate_artifact_customs.py . --write-content-lock` from the
repository root, then update that binding.
