# Release body template

Use the [presentation procedure](../agents/release-presentation.md) to turn
verified release inputs into the sections below. Replace every placeholder,
derive download rows from the actual Slate and targets, and omit inapplicable
optional sections. Unresolved required inputs keep the text a draft. Keep one
authoring source when publishing the release on multiple surfaces.

```markdown
# {{PRODUCT_AND_VERSION}}

{{RELEASE_VALUE_AND_STATUS_IN_ONE_OR_TWO_SENTENCES}}

## Downloads

{{TARGET_SELECTION_HELP_AND_ARCHIVE_CHECKSUM_LINKS}}

Follow the [installation and update guide]({{IMMUTABLE_GUIDE_URL}}).
{{ANY_REQUIRED_COMPANIONS_OR_DOWNLOAD_SELECTION_ACTION}}

## What changed

{{GROUPED_USER_CAPABILITIES_AND_PRACTICAL_IMPROVEMENTS_WITH_USEFUL_REFERENCES}}

## Upgrading

{{REQUIRED_USER_ACTIONS_AND_BREAKING_OR_COMPATIBILITY_CHANGES_IF_APPLICABLE}}

## Known limitations

{{MATERIAL_LIMITS_OF_THIS_RELEASE_AND_RELEVANT_SUPPORT_EVIDENCE}}

## Source and verification

{{SOURCE_TAG_AND_ARTIFACT_CORRESPONDENCE_SIGNING_STATUS_AND_VERIFICATION_LINKS}}
```
