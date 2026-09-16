# Provingkit

Provingkit equips coding agents with workflows for choosing workers, reviewing
changes, keeping Git history, managing pull requests, assessing dependencies,
and writing for people. Its six coordinated Agent Plugins pair instructions
with checks that make the work reviewable.

A [pinned unsigned preview](https://github.com/nisavid/provingkit/releases/tag/preview-8acd0e2af1f4)
is available for Agent Plugins/Codex, Claude Code, and Cursor. Stable release
and live host qualification remain separate gates.

## What the plugins do

Each plugin owns a part of the work:

- **[Rolecasting](plugins/rolecasting/README.md)** plans delegation, then selects
  a model and reasoning effort for the task.
- **[Tricritical](plugins/tricritical/README.md)** coordinates independent
  reviews, adjudicates findings, and repeats authorized revision and verification.
- **[Versionkeeping](plugins/versionkeeping/README.md)** creates Git checkpoints,
  publishes work, resolves conflicts, and manages worktrees and fork synchronization.
- **[Mergecraft](plugins/mergecraft/README.md)** writes GitHub issue and
  pull-request bodies and carries pull requests through publication, feedback,
  and merge.
- **[Artifact Customs](plugins/artifact-customs/README.md)** assesses third-party
  software and guides adoption, maintenance, replacement, and retirement under
  an explicit policy.
- **[Proseweaving](plugins/proseweaving/README.md)** writes and checks prose for
  clarity, evidence, and the reader's needs.

Use the Kit when you want these workflows to work together across an agent's
work on a repository. Each plugin has its own identity and version and can be
equipped individually; Provingkit names the complete set. The client or
environment supplies the tools these workflows use, such as Git access,
delegation, and model selection.

## Get started

Follow the [install, update, and rollback guide](docs/preview/install-and-update.md)
to choose a target artifact, verify its recorded hash and receipt, and register
the marketplace for your client. The guide's commands target Linux with a POSIX shell;
start with its linked installation preparation before a Linux rollout.

The preview is pinned to source commit
[`8acd0e2af1f4`](https://github.com/nisavid/provingkit/commit/8acd0e2af1f4508a0e2358d8e01f6a3db7a78ce3).
Changes on `main` do not update those artifacts. Use the named preview target
archives; GitHub's automatic source archives include development material.

Open a plugin's README above to see its skills and usage boundaries before
equipping it. Task Witness is deferred optional equipment outside this Kit;
the [release boundary](docs/release-boundary.md) explains its status and what
the available validation proves.

## Find your next step

- **Understand the design:** read the [plugin system design principles](docs/plugin-system/design-principles.md)
  and [project glossary](CONTEXT.md).
- **Check release and evidence limits:** see [source, preview, and release](docs/release-boundary.md)
  and [Amberbridge](docs/amberbridge.md), the release-evidence bridge.
- **Look up the Kit's membership:** consult the [Kit definition](release/provingkit/definition-v1.json)
  and the individual plugin READMEs linked above.
- **Contribute:** [CONTRIBUTING.md](CONTRIBUTING.md) covers source validation,
  generated artifacts, and preparing a pull request. Agents working in this
  repository start with [AGENTS.md](AGENTS.md).

## License

[MIT](LICENSE) for the repository. Individual plugins may include their own
attribution or license files.
