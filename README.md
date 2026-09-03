# Provingkit

Provingkit is a kit of plugins that make coding agents prove their work: which role and model a delegated task gets, how Git history and pull requests stay honest, how a change is reviewed and revised, how third-party components are admitted, and how the prose an agent writes to people reads. The plugins are [Agent Plugins](https://agent-plugins.org/specification) for Claude Code and Codex-style clients. Each one works on its own; the Kit is the combination that is tested together.

Provingkit is not released yet. This repository is its public source on the way to a first release, so nothing here installs today. The sections below say what each member does, where things stand, and what to expect when it ships.

## What the members do

Each member owns one part of an agent's working loop and leaves the others alone.

- **Rolecasting** chooses the worker topology and then the model and reasoning effort for a delegated task, as separate decisions backed by evidence.
- **Tricritical** reviews a change through independent critics, adjudicates their findings, and drives authorized revision until nothing actionable remains.
- **Versionkeeping** keeps Git safe: task-only checkpoints, exact-lease publication, intent-aware conflict resolution, worktree lifecycle, and fork synchronization.
- **Mergecraft** owns the pull request: reviewer-facing descriptions, guarded publication, feedback handling, readiness, merge, and stacked fixups.
- **Artifact Customs** admits third-party components deliberately, from first assessment through adoption, maintenance, and retirement.
- **Task Witness** is the code-only member that validates evidence. It has no skills to invoke, and at this stage it is production-ineligible.
- **Tidesmith** sets the standards for prose an agent writes to people and checks drafts against them. It is being ported into this repository ahead of the first release.

The members share one design: one owner per capability, evidence over assertion, and evaluation as part of design. [Plugin system design principles](docs/plugin-system/design-principles.md) gives the reasoning, and [the glossary](CONTEXT.md) gives the words this project uses, starting with the Agent Plugins terms.

## Who it is for

You run coding agents on real repositories and want them to pick roles deliberately, keep Git clean, write pull requests a reviewer can navigate, review with critics that do not share a blind spot, and bring in dependencies with a paper trail. If you only want one of those, each member's README explains what it does alone: [Rolecasting](plugins/rolecasting/README.md), [Tricritical](plugins/tricritical/README.md), [Versionkeeping](plugins/versionkeeping/README.md), [Mergecraft](plugins/mergecraft/README.md), [Artifact Customs](plugins/artifact-customs/README.md), [Task Witness](plugins/task-witness/README.md).

## Where things stand

Unreleased source stage. There is no version, tag, release, marketplace publication, installation, or runtime qualification yet, and the marketplace file at the root is a source projection rather than a publication. [What the source stage means](docs/release-boundary.md) explains that boundary, what a release will add, and why Task Witness stays production-ineligible until then.

## Get started

Today, clone the repository and read the member READMEs; the skills are plain Markdown you can read before you trust them.

After the first release, Claude Code will install members from this repository's marketplace:

```text
/plugin marketplace add nisavid/provingkit
/plugin install mergecraft@provingkit
```

Codex-style clients will load each member as a standard Agent Plugins package. The install and update guide lands with the release.

## Learn more

Understand the design: [Plugin system design principles](docs/plugin-system/design-principles.md), [the glossary](CONTEXT.md), [the Agent Plugins Specification](https://agent-plugins.org/specification).

Look something up: the member READMEs linked above, [the Kit definition](release/provingkit/definition-v1.json), and each member's `CHANGELOG.md`.

Contribute: [CONTRIBUTING.md](CONTRIBUTING.md) covers validating a source checkout, generated artifacts, and what a pull request should tell a reviewer. Agents working in this repository start from [AGENTS.md](AGENTS.md).

## License

MIT for the repository. Individual members may include their own attribution or license files.
