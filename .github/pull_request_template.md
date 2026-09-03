# Summary

<!-- State the behavior or source contract this change delivers. -->

## Boundary

<!-- Name the owning member or shared Kit boundary and the authorizing issue. -->

- Owning surface:
- Issue:
- Release, publication, installation, or live-qualification authority: none

## Provenance and compatibility

<!-- Identify derived source/history and any retained aliases or historical links. -->

- Source revision or history:
- Compatibility aliases or historical references:

## Validation

<!-- List checks run against the published revision and what they prove. -->

- [ ] The Provingkit definition and repository exclusions pass.
- [ ] Every affected member's focused tests and source validator pass.
- [ ] Supported derived locks regenerate without a diff.
- [ ] Task Witness source-shape changes, if any, carry the required independent review.

## Review checklist

- [ ] The six source members carried by this cutover remain distinct from the seven-member first release; Tidesmith enters through issue #25 after pull request #11.
- [ ] Member manifests keep independent identities and versions.
- [ ] Historical Linux or macOS inputs are not presented as current qualification.
- [ ] This change creates no Provingkit release, tag, release-manifest instance, marketplace publication, or live installation.
