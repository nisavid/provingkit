# Dependency-contract evidence and testing methods

This research supplies cases, evidence limits, and feasible experiments for [Establish evidence and testing methods for disputed dependency contracts](https://github.com/nisavid/provingkit/issues/511), under [Deliver dependency-contract selection and regression practices](https://github.com/nisavid/provingkit/issues/499). It supports the later design conversation; it does not install a policy or accept an exception for a consumer.

Research date: 2026-10-10. I read public first-party specifications, documentation, maintainer history, and retained first-party Codex changes. I also ran one constructed, local, in-memory SQLite experiment. Other experiments below are proposals. No service acceptance, installation, deployment, or production consumer was tested.

## Establish what the promise governs

The map already establishes the preference: absent a compelling benefit, prefer the stricter standard, stable, documented, specified, or declared contract, in that order, over implementation-implied behavior. Applicability comes first. A more restrictive rule from another route is not automatically the applicable promise.

The sources show why neither a version number nor a document heading is enough:

- [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html) requires a declared public API. Its incompatible-change rules address that API, and its major-zero rule permits instability. A dependency merely using three numeric components has not thereby promised SemVer, declared its entire implementation public, or made performance and byte-for-byte output stable.
- [Go's compatibility promise](https://go.dev/doc/go1compat) covers source compatibility and explicitly excludes several dependencies on unspecified behavior, bugs, operating-system interfaces, tool properties, and performance. A successful compile cannot establish a runtime semantic guarantee, binary compatibility, or unchanged latency.
- [Kubernetes' deprecation policy](https://kubernetes.io/docs/reference/deprecation-policy/) distinguishes API-group versions and stability tracks, CLI elements, feature behavior, feature gates, and metrics. It applies between official releases rather than arbitrary commits. API support lifetime and serving an endpoint are distinct from retaining the ability to decode persisted data. The [version-skew policy](https://kubernetes.io/releases/version-skew-policy/#kubectl) separately constrains client/server combinations.
- [RFC 8259, sections 4 and 9](https://www.rfc-editor.org/rfc/rfc8259.html#section-4), makes member-name uniqueness a `SHOULD`, describes divergent handling of duplicate names, and allows a parser to accept extensions. A standards argument must preserve those modal distinctions. Parser acceptance is not proof that every receiving service accepts or assigns the same meaning to the input.

For a concrete case, the useful unit of investigation is an observable claim with a consumer, dependency identity, version or revision, route, input population, relevant configuration/platform, expected semantic result, and consequence of disagreement. This is a proposed investigation aid, not a required universal record format. For example, “a native Codex loader discovers exactly these declared skills” is a different claim from “the public directory accepts this ZIP.”

## Cases that separate the evidence classes

| Case | First-party evidence and what it establishes | Practical conforming option and its cost |
| --- | --- | --- |
| Strict applicable promise: external Go struct literals | The [compatibility document](https://go.dev/doc/go1compat#expectations) warns that adding exported fields can break unkeyed external literals and recommends keyed literals. [Russ Cox's account](https://go.dev/blog/compat#struct) gives the concrete `net.TCPAddr` change and its before/after source. Working old code was insufficient evidence of protected compatibility. | Use keyed fields. The local edit is small and avoids coupling to the complete field list. This case provides little reason to retain the looser assumption. |
| Implementation detail becomes a language promise: Python dictionary order | [Python 3.6 release notes](https://docs.python.org/3.6/whatsnew/3.6.html#new-dict-implementation) explicitly warn against relying on the new order-preserving implementation. [Guido van Rossum's ruling](https://mail.python.org/pipermail/python-dev/2017-December/151283.html) and [Python 3.7 release notes](https://docs.python.org/3.7/whatsnew/3.7.html#summary-release-highlights) then establish insertion order as language behavior. This is explicit intent followed by a published promise, rather than permanence inferred from a patch. | Where the supported population includes earlier or otherwise unqualified implementations, use an explicitly ordered representation or narrow the supported population. That can add representation/conversion cost; simply assuming that all Python versions share the later promise is not equivalent. |
| Deliberate widening with a route limit: native Codex skill paths | [Commit `e12dd73`](https://github.com/openai/codex/commit/e12dd73b7d5a2aa2b8d0933a2053e7eb5eba6fbb) adds string-array skill roots for packages exposing several directories and expressly limits its scope to the core manifest/load path. Its final loader diff replaces the implicit default roots when explicit roots exist. [The preceding change](https://github.com/openai/codex/commit/1ad0d7aa4b92b8bfcae0272a29609b27fc334ad9) accepted invalid field shapes with a warning and default-root fallback, so parsing success alone cannot distinguish selection from ignored configuration. | A package conforming to the intended stricter ingestion layout needs a flat distribution projection, selection of only promoted skills, and checks for projection drift. That buys route portability but adds generation and maintenance. For the native route, retaining original selected directories avoids those costs, subject to the actual discovery obligation. Neither option has been selected by this research. |
| Wrong-route control: native loading versus portable loading and directory submission | [Codex commit `56b82e6`](https://github.com/openai/codex/commit/56b82e676cc56ccd550362fc5055c76ba3445849) deliberately branches legacy/native recursive discovery from portable direct-child discovery. [OpenAI's package guide](https://developers.openai.com/plugins/build/plugins) retains the native manifest compatibility fallback. The [submission-error reference](https://developers.openai.com/plugins/deploy/submission-errors) distinguishes directory submissions from workspace installations, while documenting string-root and direct-child requirements for its checks. | Choose and qualify the actual delivery route. A native discovery result does not clear public ingestion, and a submission rule does not prove native rejection. Shared checks may apply outside the submission portal, so that possibility still needs route-specific evidence rather than a blanket dismissal. |
| Implementation-only behavior without a stability promise: SQLite result order | [SQLite's SELECT specification](https://www.sqlite.org/lang_select.html#orderby) leaves order undefined without `ORDER BY`, and also leaves ties undefined when all ordering expressions compare equal. The [diagnostic PRAGMA](https://www.sqlite.org/pragma.html#pragma_reverse_unordered_selects) exists specifically to expose assumptions about repeatable but unpromised ordering. | Specify `ORDER BY` with enough keys to resolve meaningful ties, or consume an unordered collection if order has no product meaning. Sorting can add query cost, and choosing a tie-breaker may require a domain decision. Those costs should be compared with the actual benefit of relying on incidental visitation order. |
| An intentional, compatible change can still break a consumer | The [Go compatibility account](https://go.dev/blog/compat) documents increased time precision, changed ordering of equal sort elements, input parsing changes, and protocol changes. It distinguishes API checking from testing existing programs. Deliberate intent can explain a change without promising to preserve the behavior the consumer previously observed. | Accept any semantically valid output, normalize to the precision the consumer owns, validate the intended input language before a broader parser, or use an explicitly stable mechanism. Pinning or forking can preserve behavior but also preserves maintenance and security-update obligations. |
| Live versioned service: Kubernetes API use | The [deprecation policy](https://kubernetes.io/docs/reference/deprecation-policy/) gives different lifetime rules for GA, beta, and alpha APIs and documents warnings and migration constraints. A server response today does not erase removal rules or establish support for an arbitrary client/server pair. | Move to an applicable supported API version and test conversion and consumer semantics. Migration can entail object edits, conversion, operational coordination, or downtime. The relevant environment and authority must be identified before executing those tests. |

The Codex case above uses retained first-party commit responses and patches, examined during this research. It is not a fresh run of Codex, a rerun of upstream tests, or a fresh query of its ingestion service. The commit's obsolete summary bullet about retaining default roots conflicts with the final diff; the [review adjustment](https://github.com/openai/codex/pull/28790#discussion_r3432792362) and final code establish the narrower selection behavior. This is a concrete reason to compare narrative intent with the merged change and its tests.

## Trace intent without inventing a promise

The strongest trail in these cases combines a statement by an appropriate owner, a behavior-changing patch, tests exercising the disputed boundary, and continuity into the supported release. Python supplies a later language ruling. Codex supplies an explicit native-loader widening and a format-specific discovery branch. Go supplies a first-party account of why breaking observed behavior can remain within its promise. These are different evidentiary outcomes; they should not receive one undifferentiated “intent found” result.

A feasible bounded investigation is to read the governing current promise, the introducing or changing revision, its parent behavior, linked review discussion, relevant first-party tests, and release/deprecation notes for the supported version. Record the question each item answers and what it does not. A test for parser acceptance does not prove that declared roots control discovery. A native-loader test does not promise ingestion acceptance. A test present in source has not been executed merely because it was inspected.

I also ran a bounded unsuccessful search for an intention to preserve the insertion-like order observed in the simple unordered SQLite query below:

- Read the owning SELECT ordering rules and `reverse_unordered_selects` documentation.
- Searched public SQLite-domain material with `site:sqlite.org "SELECT" "insertion order" "guarantee"` and `site:sqlite.org "unordered" "stable" "release" "order"` on 2026-10-10. The first returned two forum results, which I did not treat as an owner's stability promise; the second returned no results.
- No promise preserving this query's current order was established in that bounded search. The owning documentation expressly reserves arbitrary order, so repeating the query or broadening the search would not repair the applicable contract.

That result is neither an exhaustive historical search nor proof of accidental implementation. It is enough to keep the inferred stability claim unestablished. No upstream question is needed to apply the existing documented ordering rule. If a later case remains consequentially ambiguous after local investigation, the next design conversation can decide whether an authorized owner question is worth its cost; this research authorizes no contact.

## Real-boundary regressions and demonstrated sensitivity

The map requires automated regression coverage for every relied-upon contract difference. Intent does not waive coverage. When intent remains unestablished, missing or failing coverage blocks reliance. The design must still locate the actual dependent operation and its owner; this requirement does not create a universal gate across unrelated work.

| Mechanism | What a useful experiment observes | Limits and practical costs |
| --- | --- | --- |
| Execute the actual local dependency through the consumer's supported entry point | Semantic output and errors from the real parser, loader, compiler, or database engine, using representative positive inputs and exclusions. | Requires a usable dependency artifact and controlled environment. A direct library call may omit an adapter the production consumer uses. Source-text assertions or a replica of the parser do not replace this run. |
| Compare supported releases and a proposed upgrade | The same consumer assertion against each claimed supported configuration; the proposed upgrade is evaluated before dependent promotion. | A sampled matrix does not establish every version in an interval. Historic artifacts may be unavailable or incompatible with the current host. Record an untested version as unqualified, not as a pass inferred from its neighbors. |
| Deliberately disturb the actual dependency boundary | Show the same oracle detecting a meaningful change: SQLite's own order reversal, a changed declared root, an excluded sentinel becoming visible, a malformed input, or selection of another real route. | A mutation must reach the relied-upon behavior. Merely changing an unrelated value or asserting that an exception is thrown elsewhere proves little. SQLite explicitly warns that reversal does not affect every query, so confirm the perturbation actually occurred. |
| Run an appropriate live or representative service probe | Actual server validation and semantic response through the intended route, under a supported client/server/configuration combination. | Needs endpoint access, authority, suitable data, and a cost/side-effect budget. A local schema validator, mock, or replay proves only its narrower behavior. An authorized test environment can still differ from production admission rules, feature gates, or version. |
| Exercise the check's propagation and unavailable states | A deliberately failing compatibility assertion prevents the named dependent action; a missing executable, absent check, unsupported version, timeout, or unusable fixture cannot silently become success. | This requires an integration test of the owning workflow, not only a test returning nonzero. The appropriate treatment of unrelated work and operational outages remains a design decision. |

[Go's API-checking and testing account](https://go.dev/blog/compat#api) provides first-party evidence that structural checks catch a different class of incompatibility from running real programs. [SQLite's diagnostic documentation](https://www.sqlite.org/pragma.html#pragma_reverse_unordered_selects) provides a concrete dependency-owned sensitivity method and its limitations.

For a stateful API, do not equate a nonpersisting check with a completed workflow. [Kubernetes server-side dry-run](https://kubernetes.io/docs/reference/using-api/api-concepts/#dry-run) runs normal request stages up to persistence and has explicit admission/side-effect requirements. It can help examine validation within an authorized environment; it cannot establish persistence, a controller's later effects, or rollback of an actual update. I ran no Kubernetes request.

For nondeterminism, compare semantic invariants rather than a single archived response or exact bytes the promise does not stabilize. Repeat across relevant seeds, scheduling, inputs, or configurations, and retain the variation and failures. More repetitions are not a proof of absent failure. The experiment owner must select populations and decision thresholds; no universal number is established here. For expensive or irreversible probes, a cheaper offline check may prepare the investigation, but it must not be relabeled as live-boundary qualification.

### Local SQLite observation

The local Python 3.14.6 runtime used SQLite 3.53.4. An in-memory database contained two inserted integer rows, `1` and `2`. The PRAGMA setting was read back before each query.

| Actual setting | `SELECT k FROM sample` | `SELECT k FROM sample ORDER BY k` | Constructed “must be [1, 2]” oracle on unordered output | Order-insensitive set oracle |
| --- | --- | --- | --- | --- |
| `reverse_unordered_selects=0` | `[1, 2]` | `[1, 2]` | Pass | Pass |
| `reverse_unordered_selects=1` | `[2, 1]` | `[1, 2]` | Fail | Pass |

This demonstrates a real engine boundary and a sensitive assertion in this constructed case. The ordered control represents stricter conformance. The set control is the harmless-detail case: when the consumer's required result is an unordered set, row sequence creates no relied-upon contract difference. Do not require the consumer to preserve that detail merely because the engine exposes it.

The experiment can be reproduced without external services or files:

```python
import sqlite3

db = sqlite3.connect(":memory:")
db.execute("CREATE TABLE sample (k INTEGER NOT NULL)")
db.executemany("INSERT INTO sample VALUES (?)", [(1,), (2,)])
results = []
for flag in (0, 1):
    db.execute(f"PRAGMA reverse_unordered_selects={flag}")
    assert db.execute("PRAGMA reverse_unordered_selects").fetchone()[0] == flag
    unordered = [r[0] for r in db.execute("SELECT k FROM sample")]
    ordered = [r[0] for r in db.execute("SELECT k FROM sample ORDER BY k")]
    assert ordered == [1, 2]
    assert set(unordered) == {1, 2}
    results.append(unordered)
assert results == [[1, 2], [2, 1]]
```

The final assertion verifies that this chosen fixture actually reversed. It is not a promised SQLite output for arbitrary queries, schemas, versions, or plans. These observations do not establish a production application's sensitivity, a supported-version range, or check propagation in a delivery workflow.

## Compare alternatives and revalidate material changes

The sources support several distinct alternatives, rather than a single rule to pin or fork:

| Alternative | Useful benefit | Cost or remaining obligation |
| --- | --- | --- |
| Conform to the applicable public contract | Removes a disputed implementation dependency, as with keyed Go literals or a complete SQLite ordering key. | Can require a representation, query, packaging, or product change. Measure its actual effect before assuming the cost is compelling. |
| Narrow the supported route/version/configuration | Makes a claim testable against a known population. | Sacrifices reach and adds version enforcement, availability, and upgrade work. Pinning a client cannot freeze an independently deployed service. |
| Use an owned adapter or projection | Preserves convenient canonical source while presenting the shape the consumer requires. | Adds transformation, drift detection, and separate output qualification. A conforming file shape alone does not prove preserved semantics. |
| Use an explicitly supported compatibility switch | Can provide a migration window without freezing the entire dependency. | The switch has its own scope and lifetime. [Go's GODEBUG documentation](https://go.dev/doc/godebug) shows that behavior can depend on toolchain, module/workspace declarations, source directives, environment, and security exceptions; version alone is insufficient. |
| Pin or maintain a fork | Can preserve essential behavior when no usable adapter exists. | Acquires update, patch, security, support, and distribution work. [Go's compatibility account](https://go.dev/blog/compat#output) describes real forks used for reproducible output and the lost automatic bug-fix benefit. |
| Migrate, retire, or decline the exception | Removes ongoing reliance where benefit does not justify the burden. | Can require migration, reduced functionality, or a new dependency. An exception with no feasible coverage cannot gain confidence merely from the inconvenience of these alternatives. |

Candidate revalidation triggers include dependency artifact changes; applicable promise or deprecation changes; route/manifest/adapter selection; client/server or platform changes; feature flags and configuration; input-population expansion; changed assertions, fixtures, or probes; and changes to the action that consumes the evidence. Each trigger needs an identified affected claim. A harmless change outside that claim should not invalidate unrelated evidence by reflex.

The proposed experiment should bind results to the actual executable/service identity and configuration it observed, the consumer candidate, inputs, assertion, and supported boundary. If an old version cannot be obtained, record the gap and investigate another supported configuration or change the support claim. A stored success is historical evidence, not a current pass. A service probe that cannot safely run leaves the live claim unresolved; it does not authorize a more invasive workaround.

## Candidate evaluation cases and measures

The later prototype and evaluation can reuse these controls without treating their acceptance criteria as already chosen:

1. A stricter applicable contract with an inexpensive conforming change: external Go keyed literals.
2. A requirement from another route: native Codex discovery versus portable discovery and directory ingestion. The method should identify the route before making a rejection claim.
3. Deliberate widening: Codex array roots, including the earlier ignored-field fallback as a negative historical case.
4. An implementation detail promoted to a promise: Python dictionary ordering, requiring the supported language version and implementation to be explicit.
5. Unpromised repeatable behavior and a bounded unsuccessful intent search: the SQLite unordered query.
6. Changed behavior detected by the same consumer assertion: SQLite order reversal or an actual changed dependency version, rather than a local parser imitation.
7. Missing or failing coverage: remove the probe, make its executable unavailable, or trigger the same assertion's failure, then observe the named dependent action's disposition.
8. A harmless implementation detail: the order-insensitive set consumer, where ordering restrictions would add no correctness benefit.
9. A live service constraint: Kubernetes API-version/deprecation and client/server skew, with dry-run and persisted behavior kept separate.

Compare ordinary practice, a simple conforming baseline, and the proposed method on the same cases and available evidence. Useful measures include correct route selection; missed meaningful disagreements; unjustified exceptions or rejection claims; false confidence in stale, replica, or insensitive tests; necessary versus unnecessary blocking; quality of the conforming alternative; investigation time; test setup/run/maintenance cost; and whether the consumer actually gains the claimed capability. None has a numeric acceptance bar fixed by this research.

Useful ablations remove one mechanism at a time: intent/history tracing, real-boundary execution, sensitivity controls, supported-population checks, material-change handling, or propagation into the consumer. Observe whether the simpler method still makes sound decisions and catches the selected failures. Keep the map's required coverage intact for any adopted reliance; an ablation is an experiment, not permission to deploy a reduced gate. Include adversarial cases where a pass is real but irrelevant: another route, a hidden default-root fallback, an unchanged fixture, a deprecation warning ignored by the consumer, or a process that skips a missing tool.

The remaining human decisions concern supported populations and consequences, what benefits justify an exception, acceptable investigation and test cost, operational ownership, and where checks can block work. This research gives those decisions concrete alternatives and experiments; it does not select an equipment owner, global evidence schema, controller, rollout target, or acceptance threshold.

## Coverage and limits

The factual investigation covers standards, versioned library/language promises, explicit implementation widening, route distinctions, implementation-only behavior, support/deprecation, feasible regression and sensitivity mechanisms, fallback costs, and material-change handling. The local SQLite experiment supplies one observed positive/negative/control comparison. It leaves the actual Provingkit consumer, integration, qualification, adversarial review, optimization, publication, installation, and adoption work to the map's later owned increments.

Public documentation was read through Firecrawl; some responses were cached on 2026-10-09. Context7 resolved the official SQLite documentation collection but returned no matching content for the ordering/sensitivity question, so the findings use the owning SQLite pages directly. Public-source reads and the local experiment do not establish comprehensive history, all supported versions, or future dependency stability. No package installation, paid/provider experiment, upstream communication, third-party state change, PR, or deployment occurred.
