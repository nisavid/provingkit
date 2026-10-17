# Developing Tricritical

This page is for people who contribute to Tricritical, fork it, or work with
its internals. It stays in the source repository and is not part of an
installed copy. The [README](README.md) is the page for people using the
plugin.

## Layout

```text
plugins/tricritical/
├── plugin.json                  # Canonical Agent Plugins v1 manifest
├── .claude-plugin/plugin.json   # Claude adapter manifest
├── agents/                      # Claude-native agent aliases, one per persona
├── references/                  # Authored shared runtime sources
├── skills/                      # Seven public skills and their reference projections
├── evals/                       # Raw evaluation corpus, fixtures, and protocol
├── task-witness-provider.json   # Terminal-evidence validator registration
├── content-lock.json            # Generated semantic content lock
├── topology.json                # Graph and dependency authority
├── README.md                    # Front page for people using the plugin
├── DEVELOPING.md                # This page
├── CHANGELOG.md
├── LICENSE
└── NOTICE
```

The release projection copies only an allowlisted subset of the plugin tree
into each target's installable plugin tree. Every target leaves out
`topology.json`, `content-lock.json`, `task-witness-provider.json`, `evals/`,
and this page. Only the `claude` target carries `.claude-plugin/plugin.json`;
the `claude` and `cursor` targets carry `agents/`, and only the
`agent-plugins` target carries `skills/*/agents/openai.yaml`. The
[release artifact projection](https://github.com/nisavid/provingkit/blob/main/docs/release-artifact-projection.md)
document describes the policy and the builder.

## Source authority and projections

`topology.json` is the sole machine-readable authority and dependency
declaration. The README's public-skill table and sibling skill links are
validated projections of that file. It is a source-stage record that release
projections omit, so installed skills rely on those validated links and skill
bodies instead of reading it. Its `schema_version` versions Tricritical's
topology shape; it is not a repository-wide interchange-schema version. The
`review` skill's `conditional_requires.witnessed` entry in that file declares
the two receipts that explicitly witnessed review adds.

The README's [adapter boundary](README.md#adapter-boundary) describes the
package-level `references/` sources and their per-skill projections, which the
content-lock writer regenerates.

## Adapter conventions

Claude Code has no standard agent component, so its native adapter auto-discovers
root `agents/*.md`; each file is an
exact minimal forwarder to one public skill. Codex consumes `skills/` and each
skill's `agents/openai.yaml`, but not root Claude agents.

Semantic skill-to-skill edges use literal public identities linked to sibling
`SKILL.md` files and remain relative and unqualified. Claude adapters, the Codex
extension, and `agents/openai.yaml` prompts use `$tricritical:<skill>` targets.

## Evaluation and validation

The raw evaluation corpus and its isolation protocol are documented in
[evals/README.md](evals/README.md). Run
`uv run --with PyYAML python scripts/validate_tricritical.py` from the
repository root after changes. That validator proves structural and corpus
declarations only; it does not enforce an external evaluation runner or prove
LLM behavior. It validates a private immutable byte snapshot and reports that
snapshot's identity. Run it only while no concurrent writer can modify the checkout;
live-tree drift detection remains an additional operational gate, not the
identity of the validated snapshot.

The validator's unit tests and the corpus and review-evidence suites run from
the repository root:

```sh
uv run --with PyYAML python -m unittest tests/test_validate_tricritical.py
python3 -m unittest tests/test_tricritical_eval_corpus.py
python3 -m unittest tests/plugins/test_tricritical_review_evidence.py
```

The semantic content lock, [content-lock.json](content-lock.json), covers
Tricritical's portable semantics and its evaluation corpus; it does not cover
the README or this page. Its SHA-256 is bound as Tricritical's content identity
in `release/provingkit/definition-v1.json`. The content-lock writer is
`uv run --with PyYAML python scripts/validate_tricritical.py . --write-content-lock`.
Run it after changing an authored shared source; it refreshes the required
per-skill projections before locking them. After it changes the lock, update
that binding.
