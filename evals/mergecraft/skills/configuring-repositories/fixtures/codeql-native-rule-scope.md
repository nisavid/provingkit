# Default CodeQL and native merge protection

Prepare the focused CodeQL proposal for public `sample-labs/query-router`. The maintainers selected default setup, JavaScript/TypeScript, the `security-extended` query suite where the current target supports that customization, and the existing native high-severity code-scanning rule for ordinary human pull requests to `main`. Keep the merge queue, bypass actors, and existing checks. Do not add an advanced workflow or another scanner.

Synthetic source and configuration snapshot:

- Application source is under `src/**/*.ts`; `catalog/**/*.json` and `docs/**/*.md` are maintained non-code contracts.
- Required check `quality/content` validates those contracts on `pull_request` and `merge_group`.
- The organization App reads `security/configurations/public-default.yml`. Its current CodeQL section says default setup, language `javascript-typescript`, and query suite `default`. The App's complete attachment record lists only `sample-labs/query-router` for this file; no other repository is attached. The writer changes named CodeQL values in place and preserves unspecified fields, so this source is the maintained target-only route. Direct repository edits are overwritten.
- The `main` ruleset enables merge queue, retains the release-bot bypass, and contains the native code-scanning rule at the selected threshold.

Supplied records:

- Same-repository PR 41 has a successful default-suite JavaScript/TypeScript analysis.
- Fork PR 42 has no CodeQL result. Selected fork contributions are recreated on a maintainer branch before queue entry.
- Dependabot PR 43 has a successful default-setup analysis; its rule record says `not evaluated`.
- A merge-group record has `quality/content: success` and no CodeQL analysis result.
- No extraction or upload record exists for `security-extended`.

Return an attributed assessment and the proposed maintained-source edit only. No source writer, GitHub setting, analysis, queue, or merge may be executed.