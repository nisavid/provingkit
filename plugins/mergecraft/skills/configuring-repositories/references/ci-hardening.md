# Project-specific CI and security checks

Use this guide when configuring or hardening the project's chosen CI route. If the user selects GitHub Actions, adapt Actions to the repository rather than substituting another provider. Derive jobs from the actual source, maintained commands, supported runtimes, and desired evidence. Honor an informed alternative configuration unless it conflicts with actual policy, cannot produce the requested evidence, or creates concrete active harm.

GitHub documentation was checked on 2026-10-08. Current documentation, account entitlements, and observed runs govern live application.

## Build the smallest useful checks

Read package manifests, lockfiles, maintainer instructions, existing workflows, generated-source rules, and validator documentation. Use their real commands and working directories. Select representative supported runtimes; expand a matrix when compatibility claims justify its cost.

| Source shape | Useful evidence to derive from the project |
| --- | --- |
| Python tooling or an agent plugin | The project's test runner and required dependencies; supported Python versions; plugin/content validators; manifest/frontmatter/resource layout; canonical-source and generated-projection equality; content identity or disposition checks where the project owns them. |
| TypeScript application or tooling | Installation through the declared package manager and lockfile; the project's type checking, tests, and relevant lint/build commands; workspace/package selection; generated output, entrypoints, and packaged assets where these are part of the shipped contract. |

Check layout and content through the owning validator instead of replacing it with a generic file-count or syntax check. A plugin can contain little executable code while its instruction bytes, references, manifests, projections, and packaging are its main behavioral surface. Code scanning does not validate those semantics. Keep source validation, tests, and security analysis as distinct evidence.

Connect jobs to the events the project needs: PR validation, trusted branch updates, selected scheduled analysis, and merge groups when a merge queue requires the check. Path filtering can save work but must agree with required-check emission; read [GitHub controls](github-controls.md) when making a job a merge requirement. [Workflow event and filter syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax).

## Choose CodeQL for the actual stack and entitlement

Check supported languages before recommending CodeQL. Python and JavaScript/TypeScript are supported; arbitrary instruction Markdown, manifest correctness, and every language/framework are not covered merely because analysis is enabled. Discover the relevant application and tooling languages, including workflow analysis when useful, from the current supported-language list. [CodeQL coverage](https://docs.github.com/en/code-security/concepts/code-scanning/codeql/codeql-code-scanning).

Separate three results: activation enables analysis; coverage establishes what sources, languages, builds, queries, and events were actually analyzed; enforcement establishes which observed result is required by the effective merge policy. Verify entitlement and permissions before activation. GitHub-hosted code scanning is available for public repositories and eligible organization-owned repositories with GitHub Code Security enabled; ordinary private Actions tests do not imply that entitlement. Preserve useful private CI when hosted CodeQL is unavailable, and report the specific missing capability. Paid activation or a plan change needs its own authority. [Advanced-setup availability and prerequisites](https://docs.github.com/en/code-security/how-tos/find-and-fix-code-vulnerabilities/configure-code-scanning/configuring-advanced-setup-for-code-scanning).

Choose default setup when its supported configuration and events meet the need; choose advanced setup when the project needs a maintained workflow, custom build, query configuration, or event control. Inspect an existing setup before changing it. In particular, current default setup excludes fork PRs; do not claim fork coverage from activation alone. [Setup types and events](https://docs.github.com/en/code-security/concepts/code-scanning/setup-types).

For advanced setup, select the language matrix, supported build mode, dependency access, source paths, analysis categories, query suites/packs, and triggers together. Builds must represent the intended code; private dependencies require an authorized access route compatible with the event's trust. Broader query suites may add findings and runtime, so choose them for the requested coverage. Observe database/extraction and analysis/upload results for each intended language and event before claiming coverage. [Workflow configuration](https://docs.github.com/en/code-security/reference/code-scanning/workflow-configuration-options), [build-mode choices](https://docs.github.com/en/code-security/concepts/code-scanning/codeql/codeql-for-compiled-languages).

## Keep untrusted execution away from privilege

Treat fork code, dependencies, build scripts, PR metadata, artifacts, and caches as inputs with their own trust. For untrusted fork tests, prefer an ordinary `pull_request` route with restricted token access and no sensitive secrets; observe applicable fork approval and event policies. If a test needs private dependencies or deployment credentials, split that dependent operation into a trusted, separately authorized route instead of granting privilege to all fork CI.

`pull_request_target` runs in the base repository's trusted context. Checking out or downloading a fork's code and then executing its tests, build, dependency hooks, or scripts can expose its secrets and token. `workflow_run` is also not a trust conversion: artifacts from an untrusted producer remain untrusted. Safer designs keep privileged PR metadata automation separate from code execution and validate narrowly consumed data before any trusted follow-up. Maintainer approval to run a workflow is not evidence that every supplied script is safe. [Privileged-event risks and alternatives](https://docs.github.com/en/actions/reference/security/securely-using-pull_request_target).

Give each job the least token permissions needed, escalating only for its specific authorized operation. Pin actions and reusable workflows to verified full commit SHAs when choosing immutable dependencies; retain a useful version annotation and update route. Pass untrusted strings as data through quoted variables or structured action inputs rather than interpolating them into executable shell text. Verify artifact origin and expected format, restrict extraction destinations, and preserve cache trust boundaries before consumption. These controls reduce concrete execution risks without requiring an unrelated security-product purchase. [Actions secure-use guidance](https://docs.github.com/en/actions/reference/security/secure-use).

## Bound runs and verify spending controls

For a no-additional-spend request, inspect the repository owner's current plan, included and consumed capacity, runner selection, storage, and applicable budgets before triggering qualification runs. Private repositories can use ordinary Actions within included capacity; excess usage can be billed. Public standard hosted-runner usage differs from larger-runner and storage costs. Self-hosting has its own infrastructure and trust costs. Do not infer a remaining allowance from a plan name or the ability to start a job. [Actions usage and billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions).

Use appropriate timeouts, limited matrices, cancellation of superseded PR runs, targeted schedules, and artifact retention to bound expected work. Scope concurrency so cancelling obsolete validation does not cancel a required release or deployment. Estimate the selected runs, then compare observed usage after execution; repeated attempts and storage are part of the cost. [Workflow timeouts and concurrency](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax).

An email alert or soft budget does not stop spend. For metered Actions, verify that an applicable budget has its stop-usage option enabled and that its scope covers the intended usage; account for budget creation timing and already accrued usage. When the necessary billing control or remaining capacity cannot be observed, report that gap and keep dependent chargeable runs pending, while continuing local work. Change billing policy only within its authorized scope. [Budget behavior](https://docs.github.com/en/billing/concepts/budgets-and-alerts), [budget scope and stop controls](https://docs.github.com/en/billing/how-tos/set-up-budgets).

## Verify the selected result

Review the final workflow/source revision through the owning review route, then exercise the authorized events and inspect actual logs, commit identity, emitted checks, language/build coverage, permissions, and usage. Include fork or queue behavior when it is part of the selected claim. Observe that failing relevant work prevents a claimed gate from succeeding, and that irrelevant changes do not leave a required check permanently missing. Distinguish local command success, hosted run success, code-scanning activation, analysis coverage, and merge enforcement in the handback.

If a required capability or authorized run is unavailable, retain the reviewable source and name the missing evidence and return contract. Finish the selected CI claim only when its evidence is current on the final source and dependencies; a copied workflow or enabled setting is preparation evidence.
