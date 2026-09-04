# Contributing to Provingkit

Contributions should leave the public source checkout reviewable, internally
consistent, and explicit about what their validation proves.

## Scope

Current changes stay within the seven source members: the six Agent Plugins
Rolecasting, Tricritical, Versionkeeping, Mergecraft, Artifact Customs, and
Tidesmith, plus the code-only Task Witness package. Keep changes within those
members, their shared validation, and the Kit's repository contracts.
Hindsight, Base Loadout, personal tools, and unrelated experiments belong
elsewhere.

Opening or merging a source change does not authorize a Provingkit release,
tag, release-manifest instance, marketplace publication, installation, or live
qualification. Propose those operations separately when their own policy and
authority exist.

## Prepare a change

1. Link the issue or decision that owns the change.
2. Update canonical source before any derived lock or projection.
3. Preserve each member's manifest identity and independent version boundary.
4. Use Conventional Commits for commit messages.
5. Run the focused commands in the README and report the checks that actually
   ran.

Do not present historical qualification inputs as current evidence. Files
under `qualification/historical/` are retained for provenance and design
review only.

## Generated artifacts

The member validators own their content locks and generated projections. When
an owning validator supports `--write-content-lock`, run that mode after the
authored source is stable, review its complete diff, then run the ordinary
validator. Never edit a digest merely to make validation green.

Task Witness source-shape evidence is not an ordinary generated lock. Any
source-shape change must satisfy the independent review requirement recorded in
`release/task-witness/source-shape-review.json`; there is no mechanical
rebaseline command.

## Pull requests

A pull request should tell a reviewer:

- what behavior or source contract changes;
- which member or shared boundary owns it;
- which issue authorizes it;
- which source revision or retained history the change derives from, when
  provenance matters;
- which compatibility aliases or historical links remain and why; and
- which source-stage checks passed at the published revision.

Keep release and runtime claims no broader than the evidence. A green
source-stage check proves only the public source contract exercised by that
check.
