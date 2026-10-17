# Developing Rolecasting

This page is for people who contribute to Rolecasting, fork it, or work with
its internals. It stays in the source repository and is not part of an
installed copy. The [README](README.md) is the page for people using the
plugin.

## Layout

```text
plugins/rolecasting/
├── plugin.json                     # Canonical Agent Plugins v1 manifest
├── .claude-plugin/plugin.json      # Validated Claude identity projection
├── task-witness-provider.json      # Dispatch-evidence owner registration
├── content-lock.json               # Generated semantic and rubric snapshot
├── evals/delivery.json             # Isolated executor/grader delivery contract
├── skills/                         # Skills, owner validator, references, and evals
├── topology.json                   # Authoritative ownership and call graph
├── README.md                       # Front page for people using the plugin
├── DEVELOPING.md                   # This page
├── CHANGELOG.md
└── LICENSE
```

The root manifest is the sole package identity and carries Codex presentation
metadata under `extensions.com.openai.interface`. The Claude manifest is an
exact projection of the common identity fields with only Claude's
`displayName` added. The single `skills/` tree is portable; Codex selectively
reads each preserved `skills/*/agents/openai.yaml` interface. Skill discovery
supplies the `rolecasting:` namespace, and every relative runtime resource
stays inside the package. The `schema_version` in `topology.json` versions
Rolecasting's local topology shape, not a repository-wide interchange schema.

The release projection copies only an allowlisted subset of this tree into
each target's installable plugin tree. Every target leaves out
`topology.json`, `content-lock.json`, `task-witness-provider.json`,
`evals/delivery.json`, each skill's `evals/` directory, and this page. Only the
`claude` target carries `.claude-plugin/plugin.json`, and only the
`agent-plugins` target carries `skills/*/agents/openai.yaml`. The
[release artifact projection](https://github.com/nisavid/provingkit/blob/main/docs/release-artifact-projection.md)
document describes the policy and the builder.

## Provider registration

[task-witness-provider.json](task-witness-provider.json) registers the
dispatch-evidence owner that the README's
[dispatch evidence](README.md#dispatch-evidence) section describes. Because no
authenticated owning harness integration is bound into the issuer identity,
the registered provider declares empty producer and issuer inventories and
retains only the active validator plus its exact renderer module.

Private tests may construct test-owned bootstrap trust to exercise historical
validation, but no Rolecasting historical trust has been installed and those
results cannot become authenticated evidence for witnessed publication.

## Validation

From the repository root, run:

```sh
uv run --with PyYAML python scripts/validate_rolecasting.py
uv run --with PyYAML python -m unittest tests/test_agent_plugins_standard.py
uv run --with PyYAML python -m unittest tests/test_validate_rolecasting.py
python3 -m unittest tests/test_rolecasting_eval_corpus.py
python3 -m unittest tests/plugins/test_rolecasting_dispatch_evidence.py
python3 -m unittest tests/plugins/test_rolecasting_native_codex.py
python3 -m unittest tests/plugins/test_rolecasting_daybreak_routing.py
```

The validator rejects Agent Plugins schema drift, duplicate keys and non-finite
JSON, malformed discovery YAML, invalid CLI arity, non-direct skill discovery,
resource escapes, component drift, non-portable content, projection or adapter
namespace drift, graph invariant violations, semantic-lock drift, grader-answer
leakage, and lexical ancestor symlinks.

The semantic content lock, [content-lock.json](content-lock.json), covers this
page and the README along with the manifests, topology, provider
registration, skills, and evaluation corpora. Its SHA-256 is bound as Rolecasting's content identity in
`release/provingkit/definition-v1.json`. After editing canonical source,
regenerate the lock with
`uv run --with PyYAML python scripts/validate_rolecasting.py . --write-content-lock`
from the repository root, then update that binding. Committed behavior
evaluation receipts live under `release/eval-receipts/rolecasting/`.
