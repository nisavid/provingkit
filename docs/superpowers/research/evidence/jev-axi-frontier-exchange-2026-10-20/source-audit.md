# Independent compatibility source audit

This is the retained first report with public links substituted for local source pointers. Links for private metadata and failure records lead to the public incident synopsis; they do not expose those original records. The original report identity is preserved in [record.json](record.json).

DONE_WITH_CONCERNS

The compatibility fixture remains useful, but it has no native baseline. The minimum next work is a bounded investigation of the current native launcher’s startup dependencies, followed by a concrete metadata-only preparation proposal. Repeating preparation against the obsolete executable identity would not resolve the evidence gap.

**Scope and source consistency**

I used `research` directly as the delegated worker, with no subdelegation. All 40 inventory files match their declared byte counts and SHA-256 digests. Sequential reads, including repeats, remained below 2 MiB. I ran no tests, builds, network requests, native commands, metadata calls, or author tasks, and wrote nothing.

The collector’s pinned seed-producer, transport, and Git-helper digests match the inventoried files. The retained ready receipt also names the matching producer, seed files, requests, and cases. This establishes consistency among those source and receipt bindings. It does not independently establish the historical review or publication join: those records are referenced by the metadata plan but are outside this inventory. The coordinator’s observation that reviewed `347d05b` and published `de90a974` carry the same pinned files remains a separate observation. [Collector, lines 24–29][collector]; [prepared receipt][receipt]; [metadata plan, lines 5–16][plan].

**Retained checks that remain useful**

- **The ordinary workload has a meaningful compatibility boundary.** Both consumers invoke the report without a format argument. The amendment requires unchanged consumer behavior and opt-in JSON while allowing internal restructuring. That supplies a concrete obligation whose preservation can be assessed independently of implementation layout. [Consumer source][consumer]; [amended request][amendment].
- **The behavioral evaluator remains a useful oracle.** It checks default and explicit text, JSON schema and selected warehouse, complete records, low-stock and archive behavior, empty selections, zero quantities, supported identities, and invalid inputs. It normalizes record order and distinguishes behavioral differences from failed observations. Endpoint source rechecks constrain which candidate the result describes. [Comparator, lines 37–49, 132–199, and 202–296][comparator].
- **Constructed contrasts remain calibration fixtures.** The supplied patches distinguish preserved behavior, changed defaults, dropped zero-stock records, and harmless restructuring/reordering. Their tests contain assertions about those selected CLI effects. They establish neither naturally occurring author mistakes nor the benefit of an intervention. [Construction record][constructed]; [constructed-candidate tests][candidate-tests].
- **Collector regressions remain machinery checks.** The test source covers once-only steering, profile and source drift, unanswered requests, final capture, Git correspondence, and selected deadline failures. Its “native CLI” case supplies synthetic instructions, skill resources, and protocol behavior; its assertions therefore do not qualify the real installed CLI or account. [Collector tests, lines 1, 48–90, and 440–587][collector-tests].
- **Accounting checks remain bounded synthetic checks.** They replace preparation and dispatch with marker writes and mock host observations. They can check the displayed producer’s selected admission decisions, but cannot establish native dispatch, complete cost capture, or enforcement of an actual episode’s limits. [Accounting tests, lines 40–112][accounting-tests].

These are retained test definitions and source contracts. No fresh passing test result was produced in this audit.

**Native evidence and current profile limits**

Both retained preparations stopped at `profile-discovery:initialize` and record zero native tasks started. Their process records show no callback-consumed stdout; the corrected-route process exited with status 1. Its stderr reports failure to create PATH aliases and a read-only-filesystem error. These records establish unsuccessful startup before a usable initialize response. They do not identify the fatal write path or prove that the alias warning caused the terminal error. [Initial failure][failure-one]; [corrected failure][failure-two]; [corrected process record][process]; [corrected stderr][stderr].

The old plan records a package-specific executable path, an October 11 identity/version observation, and the proposed `gpt-6.1-sol`/`medium` selection. Those are historical preparation inputs, not current profile discovery. The executable’s present absence is the coordinator’s observation; this inventory contains no current executable or installation inventory with which to verify it independently. [Metadata plan, lines 18–25][plan].

Within the audited collector, there is **no native executable fallback**: native preparation requires an explicitly supplied executable path and digest, verifies that file, and constructs the direct app-server command from it. Fake preparation is a separate branch with a different qualification state. This establishes no alternative route in the audited source; it does not establish that no other executable exists on the host. I selected none. [Collector, lines 187–231, 953–1000, and 1145–1171][collector].

Before a fresh native metadata proposal, the affected dependencies need rebinding:

1. One approved current executable identity and its supported launch arguments.
2. The actual effective configuration, instruction selection, enabled authoring/review resources, and connector inventory.
3. Actual support for the proposed model/effort and required metadata response shapes.
4. A fresh disposable baseline/profile/manifest join, with source, modes, requests, trigger paths, and affected reviews tied to that proposal.

The collector already describes these dependencies and rejects changed profile sources. Its metadata sequence stops before thread creation; successful preparation would still be `native-prepared-not-accepted`. [Collector, lines 408–601, 604–858, and 1166–1170][collector]. Native event timing, amendment delivery, final candidate correspondence, required review evidence, and accounting would still require a separately accepted episode. [Observation contract, lines 11–21 and 106–142][contract].

**Minimum next investigation and proposal**

Commission one finite **native-launcher startup compatibility investigation**, without starting the runtime. Its additional inputs should be one explicitly approved current executable identity and the matching launcher/app-server source or authoritative versioned documentation. Do not search for or substitute execution routes under this audit’s authority.

The investigation should answer three specific questions:

1. Which launch arguments used by `native_command()` are supported by that executable?
2. Which filesystem paths can its startup touch before replying to `initialize`, and which operations are required versus best-effort?
3. Does its app-server interface support the collector’s six preparation RPCs and expected response fields?

Its deliverable should be a source-cited startup dependency map and the smallest concrete metadata-only proposal: executable/digest, command, required local-state prerequisites, evidence destinations, bounds, and stop conditions. It should identify any necessary collector change separately and explain why it is needed. The retained read-only-filesystem error is the investigation target, not sufficient evidence to prescribe a writable-home override, permission change, or retry.

This enables a meaningful baseline in two stages. First, an approved metadata preparation could establish whether the intended ordinary authoring and review profile is available and produce a fresh bound manifest. Second, a separately accepted ordinary episode could deliver the two requests, retain the resulting candidate, evaluate behavior and completion obligations, and record observed correction/review work and costs. The source contracts already supply that sequence. [Collector, lines 633–858][collector]; [observation contract, lines 54–150][contract].

That baseline could inform a System One assignment by identifying a **specific observed obligation or distinct review step** worth comparing against a deterministic aid or narrow semantic judgment. If ordinary work completes correctly without a useful intervention opportunity, that is a valid baseline result. No current evidence supports assigning Jev or `jev-axi` a role, claiming savings, or accepting native execution.

[collector]: https://github.com/nisavid/provingkit/blob/de90a974dae5f1a18f98cf87d1f33d3e552c3da6/docs/superpowers/research/evidence/jev-axi-compatibility-seed-2026-10-07/collect_observation.py#L24
[receipt]: https://github.com/nisavid/provingkit/issues/471#issuecomment-6250680081
[plan]: https://github.com/nisavid/provingkit/issues/471#issuecomment-6250680081
[consumer]: https://github.com/nisavid/provingkit/blob/de90a974dae5f1a18f98cf87d1f33d3e552c3da6/docs/superpowers/research/evidence/jev-axi-compatibility-seed-2026-10-07/seed/bin/low-stock#L15
[amendment]: https://github.com/nisavid/provingkit/blob/de90a974dae5f1a18f98cf87d1f33d3e552c3da6/docs/superpowers/research/evidence/jev-axi-compatibility-seed-2026-10-07/requests/02-preserve-default.md#L1
[comparator]: https://github.com/nisavid/provingkit/blob/de90a974dae5f1a18f98cf87d1f33d3e552c3da6/docs/superpowers/research/evidence/jev-axi-compatibility-seed-2026-10-07/compare_behavior.py#L37
[constructed]: https://github.com/nisavid/provingkit/blob/de90a974dae5f1a18f98cf87d1f33d3e552c3da6/docs/superpowers/research/evidence/jev-axi-compatibility-seed-2026-10-07/constructed/README.md#L3
[candidate-tests]: https://github.com/nisavid/provingkit/blob/de90a974dae5f1a18f98cf87d1f33d3e552c3da6/docs/superpowers/research/evidence/jev-axi-compatibility-seed-2026-10-07/test_constructed_candidates.py#L29
[collector-tests]: https://github.com/nisavid/provingkit/blob/de90a974dae5f1a18f98cf87d1f33d3e552c3da6/docs/superpowers/research/evidence/jev-axi-compatibility-seed-2026-10-07/test_collector.py#L48
[accounting-tests]: https://github.com/nisavid/provingkit/blob/de90a974dae5f1a18f98cf87d1f33d3e552c3da6/docs/superpowers/research/evidence/jev-axi-compatibility-seed-2026-10-07/test_accounting.py#L40
[failure-one]: https://github.com/nisavid/provingkit/issues/471#issuecomment-6250680081
[failure-two]: https://github.com/nisavid/provingkit/issues/471#issuecomment-6250680081
[process]: https://github.com/nisavid/provingkit/issues/471#issuecomment-6250680081
[stderr]: https://github.com/nisavid/provingkit/issues/471#issuecomment-6250680081
[contract]: https://github.com/nisavid/provingkit/blob/de90a974dae5f1a18f98cf87d1f33d3e552c3da6/docs/superpowers/research/evidence/jev-axi-compatibility-seed-2026-10-07/observation-contract.md#L1
