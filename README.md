# Provingkit

Provingkit equips coding agents with workflows for choosing workers, reviewing
changes, keeping Git history, managing pull requests, assessing dependencies,
writing for people, and communicating with other agents. Its seven coordinated Agent Plugins pair instructions
with checks that make the work reviewable.

[Alpha 6](https://github.com/nisavid/provingkit/releases/tag/v0.1.0-alpha.6)
is available as per-plugin ZIPs for manual OpenAI and Claude account uploads.
Use the [Alpha 6 upload and update guide](https://github.com/nisavid/provingkit/blob/c557b9471f74afa82df8622313282808911453f7/docs/releases/alpha6-upload-guide.md)
to choose files, verify downloads, and confirm installation. This is an
unsigned prerelease; client support and loading follow the guide’s stated scope.

For Alpha 8 manual uploads, see the [Alpha 8 upload and update guide](docs/releases/alpha8-upload-guide.md).

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
- **[Surreal Intercom](plugins/surreal-intercom/README.md)** carries addressed peer
  messages and retained attempts. This source-stage member is not included in
  Alpha 6; current app compatibility and operating adoption remain separate.

Use the Kit when you want these workflows to work together across an agent's
work on a repository. Each plugin has its own identity and version and can be
equipped individually; Provingkit names the complete set. The client or
environment supplies the tools these workflows use, such as Git access,
delegation, and model selection.

## Get started

Follow the [Alpha 6 upload and update guide](https://github.com/nisavid/provingkit/blob/c557b9471f74afa82df8622313282808911453f7/docs/releases/alpha6-upload-guide.md)
for the current release. It distinguishes a first installation from updating
an existing plugin, then checks the saved version and fresh-session loading.
Use the named per-plugin ZIPs; GitHub's automatic source archives contain
development material. The older [preview instructions](docs/preview/install-and-update.md)
remain available as historical documentation.

Open a plugin's README above to see its skills and usage boundaries before
equipping it. Task Witness is deferred optional equipment outside this Kit;
the [release boundary](docs/release-boundary.md) explains its status and what
the available validation proves.

## Find your next step

- **Coordinate in Cloud:** use the [manual native-tree profile](docs/cloud-coordination/README.md)
  for one current thread and its child roles. Its pinned distribution and
  explicit invocation are separate from automatic startup or account-wide peers.
- **Understand the design:** read the [plugin system design principles](docs/plugin-system/design-principles.md)
  and [project glossary](CONTEXT.md).
- **Publish under a permission classifier:** read [binding actuator authority](docs/plugin-system/actuator-authority-binding.md)
  before changing a skill that pushes, opens pull requests, or files tickets.
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
