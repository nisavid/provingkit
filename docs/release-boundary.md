# What the source stage means

Provingkit's repository is an unreleased source stage. This page explains what that boundary is, what it deliberately does not claim, and what a release adds.

## The boundary

The repository does not establish a Provingkit version, tag, release, marketplace publication, installation, or runtime qualification. Its contents are public source: member packages, their validators, behavior corpora, and the contracts that bind them.

[`release/provingkit/definition-v1.json`](../release/provingkit/definition-v1.json) is the versioned definition of the Kit. It names the exact member set and binds each member to its own manifest. The repository carries a schema for a future immutable release manifest, but no release-manifest instance. The root [`marketplace.json`](../.claude-plugin/marketplace.json) is a source projection of the Agent Plugins members; its presence is not marketplace publication.

A Provingkit release is an immutable whole-Kit compatibility claim over exact, independently releasable member identities. Individual members remain independently equipable, but a partial selection is not Provingkit.

## Why source-stage validation proves less than it looks

The validators and the prepared wrapper described in [CONTRIBUTING.md](../CONTRIBUTING.md) exercise public source contracts. A green run confirms the contract that run exercised. It grants no release, installation, runtime, or host-mutation authority, and it does not qualify any member for production.

Task Witness makes the gap concrete. A later release must supply controls this repository does not own: an installed, host-owned, content-pinned, network-denied OS sandbox; review authorization bound to the candidate bytes; opaque inherited handles for private evidence; authenticated host and evaluation evidence with managed signing-key custody and anti-replay state; and independent provider authority bound to the exact candidate, policy, runtime, and endpoint. Until those gates close, Task Witness remains `production_eligible: false`, and its native qualification and final-release routes stay unavailable.

## Historical inputs

The retained Linux and macOS Task Witness material under [`qualification/historical/`](../qualification/historical/) is historical input for provenance and design review. It is not current qualification evidence.

The retained source-skill lineage manifest is historical for the same reason. It cannot qualify this source stage; [the release contract](https://github.com/nisavid/provingkit/issues/3) owns a fresh Provingkit rescout, and the manifest's mutation, receipt, and capture entrypoints stay disabled until that rescout.
