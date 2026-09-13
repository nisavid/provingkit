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
