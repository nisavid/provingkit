# Additional CI architecture opportunities

The most promising additional investigation is a production-used file identity
seam that lets exhaustive identity cases exercise their contract without repeating
the rest of repository acceptance. I rate it **Worth exploring**: the repeated
cost is measured, but equivalent acceptance has not been demonstrated. The
selected inert-decoding guard and complete-method scheduling remain independent
work; neither depends on selecting an opportunity below.

This research answers
[Find additional CI architecture improvements with an acceptance case](https://github.com/nisavid/provingkit/issues/122)
under
[Reduce Provingkit CI time while preserving acceptance](https://github.com/nisavid/provingkit/issues/120).
It proposes
directions for Ivan to select, without implementing them or specifying new
interfaces. The analysis base is
[`ad31344cdcb9891438cf1e92c27c776945bee6ab`](https://github.com/nisavid/provingkit/tree/ad31344cdcb9891438cf1e92c27c776945bee6ab).
I verified that the validator, its test module, and source workflow are identical
to the retained diagnosis base, `35d4bcac08feb818d921fb6ba0df1883e70db7e4`.

## Evidence and limits

The completed hosted source jobs took
[60m 30s](https://github.com/nisavid/provingkit/actions/runs/35344611398/job/105598158969)
and
[36m 54s](https://github.com/nisavid/provingkit/actions/runs/35348162329/job/105609591452).
Their source test runs took 59m 36s and 36m 16s, respectively. These are baseline
runs, not evidence for an architecture candidate.

I reread the retained `findings.md`, `coverage-parallelization-audit.md`,
`validator-baseline.prof`, `selected-tests-baseline.json`, and
`normalization-comparison.json`. The following figures come from that retained
local positive-validator profile, not a fresh measurement:

| Profile entry | Calls | Cumulative time |
| --- | ---: | ---: |
| Whole profile | 158,693,474 | 38.742s |
| `_validate_historical_identities` | 1 | 37.033s |
| `_normalize_identity_scan_file` | 738 | 36.900s |
| `_validate_history` | 1 | 1.436s |
| `subprocess.run`, all calls from the two Git wrappers | 566 | 1.159s |
| `_validate_release_boundary` | 1 | 0.237s |
| `_validate_adopted_history_delta_bundle` | 2 | 0.002295s |
| `_load_final_main_import_map` | 2 | 0.000290s |

Cumulative entries overlap and must not be added. Process time includes Git's
work as well as launch overhead. Profiling changes absolute timings. A separate
retained unprofiled case spent 0.082s in fixture cloning and 11.291s in validation.
The two largest evidence files accounted for about 80% of the baseline per-file
normalization measurement; that is a reason to reduce repeated work, not to omit
those files.

The selected guard's **28.2%** result is a local prototype result from alternating
complete-validator runs. It has no hosted candidate evidence and predicts no
percentage for these additional opportunities.

## 1. Deepen the file identity module — Worth exploring

**Files:** `scripts/validate_provingkit.py` and
`tests/test_validate_provingkit.py`.

**Problem.** The [fixture helper][identity-fixture] creates an isolated clone,
writes one file, and invokes the complete CLI. Thirty-two test methods use that
helper, often repeatedly inside complete subtest loops. For example,
[YAML acceptance and rejection cases][yaml-tests] repeat repository validation
for each document. The [CLI ordering][main] makes each case pay for the common
contracts and [whole-repository identity scan][identity-scan]; successful cases
also reach history validation. The file-specific implementation already has
substantial depth: [path-scoped exceptions][identity-scope],
[JSON and YAML extraction][semantic-sources], and
[normalization and frontmatter handling][normalization]. Its decision is joined
to repository inventory and allowlist checks in the repository module.

**Direction.** Explore concentrating file identity behavior behind one
production-used seam, so exhaustive vectors cross the same interface as the
repository caller. Keep repository enumeration, aggregate allowlist decisions,
CLI reporting, and full acceptance composition covered through integration
tests. This is a possible redistribution of acceptance evidence, not a proposal
to call a convenient private decoder and declare coverage preserved.

**Benefit.** Locality could put path, format, decoding, and identity decisions
together. Leverage would come from using that module in both production and the
vector cases. Testability could improve because a failing encoding case would
exercise the responsible behavior directly, without rescanning unrelated
evidence for every vector. The full CLI remains a real production adapter; a
second fictitious backend adapter would add no demonstrated value.

**Deletion test.** Deleting `assert_identity_fixture` would redistribute clone,
write, subprocess, and assertion logic across its callers: it earns its keep.
Deleting normalization helpers would likewise move real semantics into callers.
The opportunity is changing where meaningful behavior is exercised, not deleting
helpers or adding another pass-through layer.

**Required before selection.** Map every complete method and subtest to its
enforcing evidence: content/format behavior, path-scoped exceptions, enumeration,
symbolic-link rejection, original-byte allowlist hashing, CLI status and
path-bearing errors, and accepted-candidate composition. Preserve every existing
case and its expected result. Identify which integration assertions must remain
and how any relocated assertion proves the same contract. Retain the current
integration suite while evaluating that mapping; merely adding faster tests
does not reduce CI work. Compare cost only after the mapping is accepted.

**Limit.** No new seam or equivalent acceptance map is designed or qualified
here. This has the largest plausible leverage, but its savings are unmeasured.
Any proposal that changes identity acceptance evidence needs security review;
this research makes only an engineering structure and cost claim.

## 2. Acquire Git history evidence in fewer launches — Worth exploring

**Files:** `scripts/validate_provingkit.py` and its history mutation tests in
`tests/test_validate_provingkit.py`.

**Problem.** The retained positive profile records 450 calls through
[`_run_git`][git-wrappers] and another 116 through `_require_git_bytes`.
The [final-main loop][final-main-loop] and
[retained-import loop][retained-import-loop] each acquire parents, messages,
and raw tree deltas one commit at a time. This repeats acquisition mechanics
inside the history module. The 1.436s history total is materially smaller than
identity scanning, and rejected identity fixtures never reach it.

**Direction.** Explore bounded grouped acquisition of immutable Git object
evidence within one validator invocation, behind the existing history interface.
Keep current HEAD, retained refs, tags, and other mutable repository observations
fresh for that invocation. This is not a cache of successful acceptance or a
reason to reduce the complete graph.

**Benefit.** Locality could concentrate acquisition, byte framing, process
failure handling, and time limits in the Git adapter. Leverage would let the two
history loops retain their full comparisons with fewer launches. Testability
would improve if the adapter's failure cases and evidence-to-commit association
were explicit. There is one real Git adapter; a generic pluggable history
backend has no demonstrated consumer.

**Deletion test.** The existing wrappers enforce environment filtering,
replacement-object suppression, timeouts, and failures. Deleting them would
spread those obligations into callers. Consolidating duplicated wrapper setup
alone is not a performance architecture improvement; reducing acquisition
repetition while preserving the interface is the useful hypothesis.

**Required before selection.** Count launches and elapsed time after the selected
guard, then show whether grouped acquisition materially improves complete
positive and history-mutation cases. Map parent order, exact messages and
trailers, raw NUL-delimited deltas, object types, missing objects, retained refs,
reachability, replacement objects, tags, excluded paths, and process failures to
unchanged acceptance. Keep the [forged-carrier and reordered-history tests][history-tests]
and complete mutable fixtures. Bound output and execution; no silent partial
batch may pass. Obtain focused review of any changed history-evidence parsing.

**Limit.** The profile does not separate launch overhead from useful Git work.
There is no prototype, measured speedup, or security qualification for grouped
acquisition. Native command choices and output framing remain design questions.

## 3. Share one invocation's filesystem acquisition — Speculative

**Files:** the repository identity and release-manifest checks in
`scripts/validate_provingkit.py`, plus their integration tests.

**Problem.** The [identity scan][identity-scan] and
[release-manifest scan][release-scan] separately enumerate paths and read files.
The retained profile records 738 reads in the former and 739 in the latter; their
direct `read_bytes` cumulative costs are only 0.0114s and 0.0080s. The entire
release check costs 0.237s. Duplication is demonstrated, substantial savings are
not.

**Direction.** If a new profile exposes meaningful acquisition cost, explore a
single invocation's filesystem adapter feeding both policy modules from the
original bytes. Preserve their distinct file eligibility and parsing behavior:
the identity scan omits its own allowlist, while release detection examines it;
the [two JSON interpretations][semantic-sources] are not interchangeable with
the [duplicate-preserving release parse][release-scan].

**Benefit.** Locality could put file acquisition and path handling in one place;
leverage would serve two actual policy consumers. Testability would need to
cover the consumers' different eligibility and error behavior. This does not
justify a generic repository abstraction or another hypothetical adapter.

**Deletion test.** Removing one walk without relocating its policy checks loses
acceptance. Sharing acquisition could concentrate duplicated mechanics, but a
wrapper that merely dispatches two existing walks would add no depth.

**Required before selection.** Measure filesystem and parsing costs after the
selected work. Prove the same path set, bytes, symlink behavior, error precedence,
original-byte hashes, and [renamed, escaped, or duplicate-key manifest rejection][manifest-tests].
Establish the stable-input assumption and memory bound for a single invocation.
Every later invocation must inspect its own candidate and mutable fixture.

**Limit.** This is a weak performance candidate on the retained evidence. Sharing
all file bytes can raise memory use and change when mutations or failures are
observed. Keep it as fog unless measurement changes the ranking.

## Preserved acceptance and rejected shortcuts

The selected guard and scheduling changes preserve complete methods and
subtests. The additional file identity proposal requires the reviewed acceptance
mapping described above before changing how tests call the validator; unchanged
test-call structure is not assumed. Every existing case still needs equivalent
enforcing evidence. All directions preserve isolated mutable fixtures, full
history and required refs, and the [direct CLI, trigger diff, projection,
and prepared-entrypoint checks][source-workflow]. The [member jobs, artifact
projections, target builds, and derived-lock regeneration][other-jobs] establish
different obligations and remain required. The
[discovery test][discovery-test] intentionally skips runtime pytest collection
when pytest is unavailable; source CI does not install it. These opportunities
do not claim additional discovery evidence or measured scheduling gains.

I would not prioritize shared reset clones, shallower history, excluded evidence
files, cross-run acceptance caches, or removing the standalone CLI check. The
fixture measurement does not support changing isolation. Likewise, the
[history bundle and final-main map loaded during provenance][duplicate-loads]
and [loaded again during history validation][history-loads] have only
0.002585s combined cumulative cost in the retained profile, so a new evidence
cache or module for that duplication has no demonstrated payoff.

None of these candidates reopens the response persistence decision in
[ADR 0001](../../adr/0001-crash-recoverable-response-outcome-bundle.md) or the Git
operation profiles in
[ADR 0002](../../adr/0002-host-compatible-git-operation-profiles.md).

## Recommendation and procedure proposal

I would select the **file identity seam for an acceptance-mapping investigation**
first, while letting the selected scanner guard proceed independently. Grouped
Git acquisition is a smaller alternative if keeping the current test-to-CLI
relationship intact is the priority. No additional candidate earns **Strong** on
the current evidence.

A reusable acceptance-preserving CI measurement procedure is also a proposal:
bind source and environment, inventory complete methods/subtests and independent
workflow obligations, profile before restructuring, compare equivalent
candidates, and retain hosted results without treating local prototypes as
hosted evidence. If selected, its maintained source should be a repository-owned
procedure under `docs/agents/`, with one invocation pointer from
`CONTRIBUTING.md`. Consumers would be source-validator optimization and
test-scheduling tasks under
[Reduce Provingkit CI time while preserving acceptance](https://github.com/nisavid/provingkit/issues/120).
Evidence supports this local workflow; general
equipment would add maintenance and has no demonstrated second consumer outside
this repository. Ivan must decide whether to capture it and which implementation
lane owns verification and downstream invocation. This note creates no installed
guidance or new equipment.

[identity-fixture]: https://github.com/nisavid/provingkit/blob/ad31344cdcb9891438cf1e92c27c776945bee6ab/tests/test_validate_provingkit.py#L167-L192
[yaml-tests]: https://github.com/nisavid/provingkit/blob/ad31344cdcb9891438cf1e92c27c776945bee6ab/tests/test_validate_provingkit.py#L1757-L1819
[main]: https://github.com/nisavid/provingkit/blob/ad31344cdcb9891438cf1e92c27c776945bee6ab/scripts/validate_provingkit.py#L2405-L2427
[identity-scan]: https://github.com/nisavid/provingkit/blob/ad31344cdcb9891438cf1e92c27c776945bee6ab/scripts/validate_provingkit.py#L1609-L1692
[identity-scope]: https://github.com/nisavid/provingkit/blob/ad31344cdcb9891438cf1e92c27c776945bee6ab/scripts/validate_provingkit.py#L348-L446
[semantic-sources]: https://github.com/nisavid/provingkit/blob/ad31344cdcb9891438cf1e92c27c776945bee6ab/scripts/validate_provingkit.py#L704-L767
[normalization]: https://github.com/nisavid/provingkit/blob/ad31344cdcb9891438cf1e92c27c776945bee6ab/scripts/validate_provingkit.py#L770-L832
[git-wrappers]: https://github.com/nisavid/provingkit/blob/ad31344cdcb9891438cf1e92c27c776945bee6ab/scripts/validate_provingkit.py#L1881-L1935
[final-main-loop]: https://github.com/nisavid/provingkit/blob/ad31344cdcb9891438cf1e92c27c776945bee6ab/scripts/validate_provingkit.py#L2144-L2181
[retained-import-loop]: https://github.com/nisavid/provingkit/blob/ad31344cdcb9891438cf1e92c27c776945bee6ab/scripts/validate_provingkit.py#L2225-L2258
[history-tests]: https://github.com/nisavid/provingkit/blob/ad31344cdcb9891438cf1e92c27c776945bee6ab/tests/test_validate_provingkit.py#L1127-L1457
[release-scan]: https://github.com/nisavid/provingkit/blob/ad31344cdcb9891438cf1e92c27c776945bee6ab/scripts/validate_provingkit.py#L1828-L1869
[manifest-tests]: https://github.com/nisavid/provingkit/blob/ad31344cdcb9891438cf1e92c27c776945bee6ab/tests/test_validate_provingkit.py#L2666-L2744
[source-workflow]: https://github.com/nisavid/provingkit/blob/ad31344cdcb9891438cf1e92c27c776945bee6ab/.github/workflows/provingkit-source.yml#L19-L63
[other-jobs]: https://github.com/nisavid/provingkit/blob/ad31344cdcb9891438cf1e92c27c776945bee6ab/.github/workflows/provingkit-source.yml#L65-L237
[discovery-test]: https://github.com/nisavid/provingkit/blob/ad31344cdcb9891438cf1e92c27c776945bee6ab/tests/test_validate_provingkit.py#L2860-L2880
[duplicate-loads]: https://github.com/nisavid/provingkit/blob/ad31344cdcb9891438cf1e92c27c776945bee6ab/scripts/validate_provingkit.py#L1416-L1417
[history-loads]: https://github.com/nisavid/provingkit/blob/ad31344cdcb9891438cf1e92c27c776945bee6ab/scripts/validate_provingkit.py#L1996-L1999
