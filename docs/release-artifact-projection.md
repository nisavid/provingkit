# Release artifact projections

Provingkit keeps canonical plugin sources under `plugins/`. Those trees include
evaluation corpora, fixtures, content locks, topology records, and development
documentation. They are source material, not installable plugin trees.

`scripts/build_release_artifacts.py` is the CI/DevOps projector. It runs before
publication, never during a harness install. The checked-in
`release/artifact-projection-policy-v1.json` is the inclusion policy for each
target. The projector copies only the allowlisted runtime files, generates the
target marketplace catalog, and writes `RECEIPT.json` beside the candidate.

The receipt binds a candidate to the full source commit, its human-facing
`preview-<short-sha>` label, builder revision, target harness, plugin slate,
policy digest, file inventory, and a versioned canonical tree digest. A slate is
all-or-nothing: `task-witness` is code-only and cannot be projected as an
installable plugin. The inventory is audit evidence emitted by the projector;
an operator chooses only the source channel/ref, target, and slate.

## Building a candidate

From a clean checkout, CI can stage each target into a fresh workspace:

```sh
python scripts/build_release_artifacts.py --target agent-plugins --output "$RUNNER_TEMP/provingkit-agent"
python scripts/build_release_artifacts.py --target claude --output "$RUNNER_TEMP/provingkit-claude"
python scripts/build_release_artifacts.py --target cursor --output "$RUNNER_TEMP/provingkit-cursor"
```

Use `--channel preview` for a pinned pre-release candidate, `--channel main`
for a moving main-channel projection, or `--channel release` for a future
release. Use `--slate proseweaving` for a one-plugin candidate. The command
fails if the output exists unless `--force` is supplied, and refuses symlinks
or files outside the policy.

The generated roots are directly consumable by their corresponding marketplace
clients:

* Agent Plugins/Codex: `.agents/plugins/marketplace.json` and `plugins/*`.
* Claude Code: `.claude-plugin/marketplace.json` and `plugins/*`.
* Cursor: `.cursor-plugin/marketplace.json` and `plugins/*`.

Publish the candidate tree or archive and its receipt together. Harness update,
install, cache, and cleanup behavior remains the harness's concern. A pinned
preview is the reproducibility default. A `main` candidate is intentionally
moving: each resolved source commit produces a new receipt and artifact digest.

## Receipt and mode preservation

Qualification, publication, and rollout transfer the complete root
`RECEIPT.json` as exact bytes and retain its lowercase SHA-256; they do not
parse and reserialize the receipt. Each stage verifies the root path with
`lstat`, without following symbolic links, and requires a regular file. This
is not a link-count check and does not prohibit hard links.

`provingkit-tree-v1` excludes only the root `RECEIPT.json` and binds each
sorted relative path and file bytes. It does not bind mode bits. Publication
therefore ships the reviewed target mode manifest with the candidate and
preserves those modes in the archive. After publication, read back the
candidate, complete receipt bytes, and mode manifest; verify the receipt hash,
inventory, and tree digest; and compare every published file byte and mode
with the qualified inputs before rollout.

These receipts provide unsigned integrity evidence. They do not authenticate
custody or the builder, create a signed release, grant Task Witness authority,
or qualify an installed client or live host.
