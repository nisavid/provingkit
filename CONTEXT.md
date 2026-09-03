# Provingkit

Provingkit is a coordinated Kit of agent plugins built around constraining vibes with verification, and a proving ground for architectures that may later become generic Agentworks equipment. Where the [Agent Plugins Specification v1.0.0](https://agent-plugins.org/specification) defines a term, its definition governs here; Claude Code's equivalent is noted second.

## Language

### Packaging

**Plugin**:
A self-contained directory with a manifest and optional components. Claude Code uses the same word; its native package additionally carries an adapter manifest.
_Avoid_: Package (as the unit's name), bundle, extension

**Plugin root**:
The top-level directory of a plugin. Every path a client resolves from the package stays inside it.

**Manifest**:
The `plugin.json` at the plugin root, carrying the plugin's canonical identity and metadata. Claude Code's `.claude-plugin/plugin.json` is an adapter manifest projected from it, never a second identity.
_Avoid_: Metadata file, package descriptor

**Component**:
A skill or MCP server supplied through one of the two component types the specification standardizes.
_Avoid_: Feature, capability

**Skill**:
A direct child of `skills/` containing `SKILL.md`, conforming to the Agent Skills specification; its `scripts/`, `references/`, and `assets/` are resources of that skill. Claude Code surfaces the same skills and also loads flat-file "commands", which are native components here.
_Avoid_: Command, prompt

**MCP server**:
A server entry in the plugin's `mcp.json`. Claude Code reads the same shape from `.mcp.json` or a `mcpServers` block.

**Client**:
A tool that discovers, installs, loads, and executes plugin components, such as Claude Code, Codex, or Cursor. This repository says *harness* for the same tool when the topic is its runtime behavior rather than plugin loading.

**Client extension**:
Client-specific manifest data under a reverse-domain extension namespace in `extensions`, a same-named top-level directory, or both. The standard assigns it no portable semantics; the owning client does.
_Avoid_: Vendor data, custom fields

**Native component**:
A feature one client packages that the specification does not standardize: Claude Code agents, hooks, and commands; Codex apps and hooks; Cursor rules.
_Avoid_: Extra component, plugin feature

**Adapter manifest**:
A client-native manifest retained only because that client cannot consume the standard package or needs a native component. It is a validated projection of the manifest.
_Avoid_: Client manifest, secondary manifest

**Marketplace**:
Claude Code's catalog of installable plugins, declared in `.claude-plugin/marketplace.json` at the repository root. The specification defines no marketplace; this one lists the Kit's prompt-bearing plugins for Claude Code only.
_Avoid_: Registry, catalog, store

**Package support artifact**:
A README, license, changelog, topology, eval corpus, content lock, receipt, or validation file that ships with or validates a plugin without being a component.

**Ambient runtime capability**:
A facility of the client or environment that a skill's instructions rely on but the plugin does not provide: shell and file access, Git or forge access, user elicitation, delegation, model selection, browser or computer use, scheduling.
_Avoid_: Plugin capability, feature

### Kit and release

**Provingkit**:
The coordinated Kit of Rolecasting, Tricritical, Versionkeeping, Mergecraft, Artifact Customs, and Task Witness. *The Kit* is its shorthand. Task Witness is the code-only member: a manifest-only plugin whose control plane ships through its own deployment route.
_Avoid_: Suite, bundle, the six

**Release**:
An immutable whole-Kit compatibility claim over exact, independently releasable member identities. A partial selection is not Provingkit.
_Avoid_: Version (for the Kit as a whole), drop

**Slate**:
The set of plugins a release comprises. It is frozen before installation and live verification begin.
_Avoid_: Roster (for plugins), lineup, membership

**Roster**:
The set of skills a plugin carries.
_Avoid_: Slate (for skills), skill list

**Projection**:
An artifact derived from canonical source and verified against it byte for byte or semantically: an adapter manifest, a per-skill copy of a shared reference, a generated README block. Projections are regenerated, never edited.
_Avoid_: Copy, mirror, duplicate

**Content lock**:
The recorded digests that pin a plugin's canonical source and behavior-evaluation evidence at a candidate revision. The plugin's validator writes it.
_Avoid_: Lockfile, checksum file

**Topology**:
A plugin's `topology.json`: its sole machine-readable map of components, their calls, authority, and ownership.
_Avoid_: Dependency graph, call map

**Candidate**:
The exact bytes proposed for qualification and release. Evidence bound to a candidate goes stale when those bytes change.
_Avoid_: Build, snapshot

**Receipt**:
A recorded, independently checkable result of a release or deployment step, bound to the exact inputs it covers.
_Avoid_: Log, report

### Source and evidence

**Source skill**:
A skill maintained outside the Kit, such as one of Ivan's dotfiles-managed skills, whose behaviors feed a canonical plugin. Each of its contributions receives a disposition.
_Avoid_: Upstream skill, legacy skill

**Disposition**:
The terminal ruling on one source contribution, with evidence: adopted, corrected, superseded, or intentionally excluded.
_Avoid_: Status, verdict

**Disposition ledger**:
The machine-checked record of every source contribution's disposition and evidence. A release is forbidden while any contribution is undisposed.
_Avoid_: Tracking sheet, migration list

**Refresh contract**:
The requirement to rescout upstream source changes at the last responsible moment before candidate qualification and promotion, and to invalidate downstream evidence whenever candidate bytes change.
_Avoid_: Sync policy, update rule

**Rescout**:
Screening the installed instruction library for material changed since the last completed rescout that may need to feed a canonical plugin.
_Avoid_: Audit, re-scan

**Base Loadout**:
The portable declaration in `nisavid/agents` that selects a Provingkit release; it is that repository's only Loadout.
_Avoid_: Profile, preset

**Host Binding Profile**:
The dotfiles-owned, host-specific binding that materializes a selected Loadout on one machine.
_Avoid_: Host config, machine profile

**Agent Equipment**:
Skills, MCP servers, plugins, scripts, policy frameworks, workflows, agent roles, and other tools an agent or agentic system can equip.
_Avoid_: Tooling, agent tools

**Agentworks**:
The formal generic Agent Equipment project, with *the Works* as its shorthand. Provingkit architectures may graduate into it after independent use and conformance evidence.
_Avoid_: Agent Armory, the Armory
