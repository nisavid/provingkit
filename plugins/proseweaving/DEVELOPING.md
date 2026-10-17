# Developing Proseweaving

This page is for people who contribute to Proseweaving, fork it, or work with
its internals. It stays in the source repository and is not part of an
installed copy. The [README](README.md) is the page for people using the
plugin.

## Layout

```text
plugins/proseweaving/
├── plugin.json                  # Canonical Agent Plugins v1 manifest
├── .claude-plugin/plugin.json   # Claude adapter manifest
├── agents/proseweaver.md        # Claude-native agent alias
├── content-lock.json            # Generated semantic content lock
├── evals/delivery.json          # Plugin delivery contract
├── skills/writing-for-people/   # The public skill, its references, and its evals
├── topology.json                # Components, calls, and ownership
├── README.md                    # Front page for people using the plugin
├── DEVELOPING.md                # This page
├── CHANGELOG.md
└── LICENSE
```

## Adapter boundary

Root `plugin.json` and `skills/` are the canonical Agent Plugins plugin root;
`.claude-plugin/plugin.json` is a projection of the same identity. Skill-to-skill
edges use literal public identities linked to sibling `SKILL.md` files. Codex
adapters and each skill's `agents/openai.yaml` use `$proseweaving:<skill>` targets.
The root `agents/proseweaver.md` file is a Claude-native adapter and is not a
portable Agent Plugins component. The README's
[public skills](README.md#public-skills) roster is a projection generated from
`topology.json` by the content-lock writer.

The release projection copies only an allowlisted subset of the plugin tree
into each target's installable plugin tree. Every target leaves out
`topology.json`, `content-lock.json`, `evals/`, each skill's `evals/`
directory, and this page. Only the `claude` target carries
`.claude-plugin/plugin.json`; the `claude` and `cursor` targets carry
`agents/`, and only the `agent-plugins` target carries
`skills/*/agents/openai.yaml`. The
[release artifact projection](https://github.com/nisavid/provingkit/blob/main/docs/release-artifact-projection.md)
document describes the policy and the builder.

## Validation

`python -m unittest tests.test_validate_proseweaving` exercises the focused
contract suite. `python3 scripts/validate_proseweaving.py .` validates the plugin from the
repository root: manifest identity and projection, topology, skill contracts,
the generated roster projection, inventory, portability, and the semantic content lock.
`evals/delivery.json` governs plugin delivery, while
`skills/writing-for-people/evals/evals.json` carries the skill behavior corpus.
The plugin declares no Task Witness provider yet; publication eligibility and
inclusion in a release slate is decided outside this plugin.

The semantic content lock, [content-lock.json](content-lock.json), covers this
page and the README along with the manifests, topology, skills, and evaluation
corpus. Its SHA-256 is bound as Proseweaving's content identity in
`release/provingkit/definition-v1.json`. After editing canonical source,
regenerate the roster projection and the lock with
`python3 scripts/validate_proseweaving.py . --write-content-lock` from the
repository root, then update that binding. Committed behavior evaluation
receipts live under `release/eval-receipts/proseweaving/`.
