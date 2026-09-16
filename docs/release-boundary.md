# Source, preview, and release

Provingkit's pinned unsigned preview provides installable artifacts from one
qualified source commit. Source validation, preview publication, live host
qualification, and a stable Kit release establish different claims.

## The Kit and its source

A Provingkit release is an immutable whole-Kit compatibility claim over exact,
independently releasable plugin identities. Individual plugins can be equipped
separately; a partial selection is not Provingkit.

[`release/provingkit/definition-v1.json`](../release/provingkit/definition-v1.json)
is the versioned definition of the Kit. It names the exact member set and binds
each member to its own manifest. The repository contains a schema for a future
immutable release manifest, but it contains no release-manifest instance.

The root [`marketplace.json`](../.claude-plugin/marketplace.json) is a source
projection of the six Agent Plugins for Claude Code. Its presence is not
marketplace publication.

## The pinned preview

The [unsigned preview](https://github.com/nisavid/provingkit/releases/tag/preview-8acd0e2af1f4)
is bound to source commit
[`8acd0e2af1f4508a0e2358d8e01f6a3db7a78ce3`](https://github.com/nisavid/provingkit/commit/8acd0e2af1f4508a0e2358d8e01f6a3db7a78ce3).
It has target artifacts for Agent Plugins/Codex, Claude Code, and Cursor.
Those artifacts remain fixed when repository source or documentation changes.

The CI-only [artifact projection process](release-artifact-projection.md)
excludes development material and emits a receipt bound to the source commit,
target, slate, inventory, and deterministic artifact digest. The
[install, update, and rollback guide](preview/install-and-update.md) identifies
the published archives and their verification records.

Stable release and live host qualification remain separate gates.

## Source checks and release evidence

The validators and prepared wrapper in
[CONTRIBUTING.md](../CONTRIBUTING.md#validate-a-source-checkout) validate public
source contracts. A green run proves only the contract exercised by that run.
These checks do not grant release, installation, runtime, or host-mutation
authority. Opening or merging a source change does not authorize those operations.

[Amberbridge](amberbridge.md) is the release-evidence bridge between the public
Kit and its private deployment context. Its contracts and tests are present;
live release routes remain unavailable in this source stage.

Native `public-release` and optional Task Witness qualification routes remain
unavailable. A later release must supply controls that this repository does
not own: an installed, host-owned, content-pinned, network-denied OS sandbox;
review authorization bound to the candidate bytes; opaque inherited handles
for private evidence; authenticated host and evaluation evidence with managed
signing-key custody and anti-replay state; and independent provider authority
bound to the exact candidate, policy, runtime, and endpoint. Until those gates
close, optional Task Witness equipment remains unavailable.

## Historical and deferred inputs

Task Witness is deferred optional equipment. It is outside the current Slate
and is not a dependency of the ordinary plugins; see
[issue #61](https://github.com/nisavid/provingkit/issues/61).

The retained Linux and macOS Task Witness material under
[`qualification/historical/`](../qualification/historical/) is historical input.
It is not current qualification evidence and does not make Task Witness
production-eligible.

The retained source-skill lineage manifest is also historical. It cannot
qualify this source stage; [issue #3](https://github.com/nisavid/provingkit/issues/3)
owns a fresh Provingkit rescout. Its mutation, receipt, and capture entrypoints
remain disabled until that rescout.
