# Tidesmith port reconciliation

Issue #25 ports the final source states from PR #97 (merge commit
`5a3c829`) and PR #98 (merge commit `d292aa9`) into Provingkit. This record
classifies every changed source surface against the destination contract.
The review-writing changes from PR #96 have their own adjacent reconciliation
record.

## Dispositions

| Source change | Disposition | Destination result |
| --- | --- | --- |
| PR #97 plugin manifests, license, README, changelog, topology, and delivery eval contract | corrected | Retain the Tidesmith identity and version, rewrite repository URLs to Provingkit, and compose the bootstrap with the skill already present in PR #98. |
| PR #97 validator and focused tests | corrected | Retain the source contract, rewrite destination identities, and extend it to validate the landed `writing-for-people` roster, resources, and behavior evals. |
| PR #97 `content-lock.json` | intentionally excluded | Discard the source lock bytes and regenerate the semantic lock from the destination plugin root through `scripts/validate_tidesmith.py --write-content-lock .`. |
| PR #98 `writing-for-people` skill, references, adapter metadata, behavior evals, and fixtures | adopted | Preserve the final skill behavior and evaluation corpus under `plugins/tidesmith/skills/writing-for-people/`. |
| PR #98 README, changelog, and topology updates | corrected | Compose them with the destination bootstrap, current Provingkit terminology, and the generated roster projection. |
| PR #98 lock update | intentionally excluded | Replace the source lock with the destination-generated lock after all authored Tidesmith source is stable. |

Issue #25 also adds the destination-only marketplace, Kit-definition,
public-release registration, plugin-eval calibration, workflow, and
seven-member documentation bindings required by current Provingkit. Those are
corrective destination integration, not source changes attributed to PR #97
or PR #98.

## Boundary

This reconciliation ports source and source-stage policy only. It creates no
release, tag, credential, installation, publication, or live-host change, and
it does not remove the old source copies.
