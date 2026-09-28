# Developing Versionkeeping

This page is for people who contribute to Versionkeeping, fork it, or work with
its internals. It stays in the source repository and is not part of an
installed copy. The [README](README.md) is the page for people using the
plugin.

## Layout

```text
plugins/versionkeeping/
├── plugin.json                      # Canonical Agent Plugins v1 manifest
├── .claude-plugin/plugin.json       # Claude adapter manifest
├── skills/                          # Shared harness-neutral core
│   └── checkpointing-and-publishing-git-work/
│       ├── references/              # Publication, cleanup, and eval integrity
│       └── scripts/                 # Publication and deletion planner/executor routes
│   └── resolving-merge-conflicts/    # Interpretation and authorized resolution edits
├── topology.json                    # Canonical component, call, and operation map
├── README.md                        # Front page for people using the plugin
├── DEVELOPING.md                    # This page
├── CHANGELOG.md
└── LICENSE
```

The Claude manifest and `skills/*/agents/openai.yaml` are thin client adapter
surfaces around the standard package. Shared skills do not assume a client-specific installation location:
they resolve helper scripts from this plugin root.
The `schema_version` in `topology.json` versions Versionkeeping's local
topology shape, not a repository-wide interchange schema.

The release projection copies only an allowlisted subset of this tree into
each target's installable plugin tree. Every target leaves out
`topology.json` and this page. The
[release artifact projection](https://github.com/nisavid/provingkit/blob/main/docs/release-artifact-projection.md)
document describes the policy and the builder.

## Repository release validation

The [README](README.md#package-validation) lists the package checks, which also
run in an installed copy.

Repository maintainers additionally run `python3 scripts/validate_versionkeeping.py`
and `python3 -m unittest tests/test_validate_versionkeeping.py` from the
repository root. Canonical development and release evidence lives at
`evals/versionkeeping/`, `tests/plugins/versionkeeping/`, and
`release/plugin-content-locks/versionkeeping.json`; none of it is installed in
the runtime root. The validator reads [topology.json](topology.json) as the
canonical component and ownership inventory and verifies the generated semantic
content lock.

The evaluation-gate regression suite is repository-only evidence, not an
installed runtime test. From the repository root, run
`python3 tests/plugins/versionkeeping/checkpointing-and-publishing-git-work/test_eval_gate.py`.
