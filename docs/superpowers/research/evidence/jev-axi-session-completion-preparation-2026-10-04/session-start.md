# SessionStart source path and observation prerequisites

The frozen dependency closes the SessionStart construction gap. It shows a no-argument jev-axi status command, not a Jev assessment or a task-specific readiness probe. Native delivery, useful discovery reduction, and tool-selection benefit remain unobserved by this increment. All 37 frozen inputs matched their SHA-256 before and after research. No source, hooks, tests, configuration, credentials, network, or provider calls were executed or inspected beyond the frozen source files.

## Command construction and delivery

The frozen jev-axi snapshot identifies version 0.7.2; its manifest requests `axi-sdk-js ^0.1.12`, and its lock resolves 0.1.12. The supplied SDK package also identifies 0.1.12. These source identities do not establish that an eventual installed jev-axi build or native harness uses these exact bytes (`jev-axi/package.json:27–53`, `pnpm-lock.yaml:17–19,510–512`, `axi-sdk-js/package.json:1–29`).

`jev-axi/src/commands/meta.ts:244–250` invokes `installSessionStartHooks({scope})`; it supplies neither custom command arguments nor an error callback. The SDK infers identity from the process entrypoint, skips an unrecognized identity or an entrypoint rejected by its policy, and rejects development TypeScript entrypoints. It chooses a plain binary name only when PATH/realpath or Windows shim matching identifies the same executable; otherwise it retains the absolute entrypoint. The hook command contains no arguments (`axi-sdk-js/dist/hooks.js:317–469`).

For Claude Code and Codex, the SDK writes command-type SessionStart entries with an empty matcher and a default ten-second timeout. User scope targets user hook files; project scope targets project hook files but still ensures the user's Codex hooks feature flag. There is no event-payload parser, session-ID filter, or cwd override in this command construction. Actual harness invocation, effective cwd, event matching, timeout enforcement, and model-context delivery require observation (`dist/hooks.js:8–62,282–294,447–508`).

OpenCode uses a generated plugin rather than that native hook entry. It spawns the same executable without arguments, uses the directory supplied to plugin initialization, falling back to process cwd when absent, inherits the environment, ignores stdin, and caches the resulting string by session ID (or a shared fallback key) in memory. Each system transform appends the cached ambient header and nonempty string. Its cache has no TTL or refresh path here; even an error string is cached. The native meaning of that supplied directory is not established here. This is generated source, not proof of native plugin acceptance (`dist/hooks.js:183–266`).

## Payload and recurring work

No-argument CLI dispatch selects `homeCommand`. The jev-axi wrapper first renders its object as TOON plus readable help; the SDK then prepends its executable/description header. SDK object output protects the header's bin and description fields, but the jev-axi home handler returns a rendered string. Neither path filters content by SessionStart payload or task relevance (`jev-axi/bin/jev-axi.ts:1–8`, `src/cli.ts:86–90,106–151`, `src/commands/common.ts:45–56`, `axi-sdk-js/dist/cli.js:60–63,110–121,179–197`, `dist/output.js:9–13,28–33`).

The constructed payload includes key presence/source, selected model, the last 24 hours' local usage summary, response-cache file count, command examples, output-column help, and optional update notices. Key presence is not authentication or service readiness. Model selection is configuration resolution, not a current model-capability query. Cache count is a directory listing, not verification that each response remains usable. Repeated command keys overwrite earlier entries: the several setup examples collapse to the last setup entry in the command table. The description's latency/calibration language is advertised text, not a measured result (`src/commands/home.ts:7–25`, `table.ts:2–24`, `meta.ts:173–176,318–324`, `src/cli.ts:35–36`).

Key lookup searches environment, then dotenv files from process cwd toward the Git/filesystem root, then persistent configuration. The source supplies no chdir from event payload, so a wrong inherited cwd can select different dotenv context. This audit read the lookup implementation, not actual keys or configuration (`src/config.ts:111–166`).

The home view awaits jev-axi's daily npm registry check. It is disabled by configuration, NO_UPDATE_NOTIFIER, or CI; a recent local timestamp skips it. Otherwise it fetches the latest-version endpoint with a one-second abort signal and records an attempt even on fetch failure, provided local state can be written. A failed state write can leave later invocations paying the lookup again. These are source timeout and caching policies, not observed duration guarantees (`src/update.ts:5–7,16–27,40–65`).

Local reads are not necessarily free of writes: config/state/cache path resolution can rename legacy directories; usage reading can migrate a ledger, including a copy fallback. Usage summaries estimate cost using configured/default prices and exclude cached entries from billed-token totals; they are not verified billing or complete research accounting (`src/config.ts:39–86`, `src/usage.ts:38–77,91–136`).

The separate built-in `update` command is not run by SessionStart. It can query the registry, fall back to npm view, and, unless checking only or returning a manual plan, spawn an installer. The passive notice instead tells the agent not to upgrade autonomously (`axi-sdk-js/dist/cli.js:71–75,123–139`, `dist/update.js:314–415,501–584`, `jev-axi/src/update.ts:72–75`).

## Skips and failures

Installation catches per-target failures and reports them only through an optional callback; this caller provides none and still returns an installed-status description. Status checks recognize managed markers rather than proving invocation or successful delivery. OpenCode turns timeout, spawn error, and nonzero exit into injectable error text; empty successful stdout adds nothing. CLI handler errors become stdout error output and a nonzero exit code. Missing API credentials produce home-view skip/report guidance rather than a failed readiness probe (`dist/hooks.js:296–315,447–508,517–584`, `dist/cli.js:110–145`, `jev-axi/src/commands/home.ts:20–25`).

## Minimal observation proposal

Under the accepted SessionStart bars recorded in the frozen tracker and purpose draft, a proposal first needs one named harness/version, exact installed executable and dependency identities, supported hook scope/event, effective cwd/environment policy, and a bounded task with a plausible discovery need. Freeze permitted metadata/network effects and evidence retention before any run; do not silently replace this path with a narrower implementation.

Capture the actual emitted bytes and native model-visible context, invocation count, cache/update state transitions, failures/skips, and downstream discovery/tool actions. Include repeated starts and stale or unavailable information where supported. Compare ordinary discovery, retrieval when needed, recurring injection, and omission. A useful consumer action would be selecting an appropriate available command with less discovery work, or correctly skipping unavailable capability, while preserving task quality and avoiding unnecessary questions or steering. Merely displaying command names or a key-presence label does not establish that effect.

Account separately for process startup, local reads/migrations, registry attempts, recurring context tokens, downstream expensive-model work, interruptions, and maintenance; unknown components remain unknown. The maintained comparison contract requires adequate context and whole-task accounting before assignment. The next consumer is the SessionStart observation-scope decision following [Establish context and baselines for session-start and completion checks](https://github.com/nisavid/provingkit/issues/399). No experiment, utility finding, live change, security claim, or architecture decision follows from this brief.

## Frozen dependency identities

SHA-256 identities for the supplied axi-sdk-js 0.1.12 files:

| Package-relative file | SHA-256 |
| --- | --- |
| package.json | 7e931285e8bcf75f366f9bb02ea822934013e64e734d225ca4f9b072b1596860 |
| README.md | 9cd4b812df424516948109b2f8339ed4bb51bf49a96c9970fded4d2a165c87a8 |
| dist/fast-path.js | a3733ac9e099d3d2f09183f1ad2977a7e9613fa3dd5a207ee5f5f838efbfa840 |
| dist/index.js | 265f9730c582cb1e8e19dc832f3603006e52d73f22e79b62a995cec400a84b2e |
| dist/output.js | 87aea7c181989b802af98cbe895f9aae1e72d4bca039dafca6f975ff15fc482c |
| dist/hooks.js | b200af66e7fdfb02bd04c4d5b4914c84bd0d54e5cef754267c7d08c5c351f4ec |
| dist/errors.js | ae30f95f0a82cfbdb51051575ce713ad90acd8b89138c64fa26e76a8716fda4f |
| dist/cli.js | 7bda640cc33a6f5226e60b7df2ef7ea8c765431c0e89a267273993370bdd8121 |
| dist/update.js | 337c6ac93156d50e6ac2375ac436a7a94e87d9bd15d15d030dc060f65b6c88e4 |

The SDK lock resolves its TOON dependency to 2.3.1; jev-axi directly resolves 4.1.1. Serializer implementation and other unfrozen imports were not supplied, so this source trace establishes calls and assembly, not exact rendered/native output qualification. The maintained method identities are `handling-sys1-incidents/SKILL.md` SHA-256 `1d28f851542a0c7a11a190772630c941f224de5da7b4a776c3e62bcc6a3769ac` and `references/comparison-contract.md` SHA-256 `9f876cd27c4bd6fe82d56feabc6e31e05d029d7cac18f9651194218e2e1aa981`.
