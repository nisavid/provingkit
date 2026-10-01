# Native supervision preflight source

This checkpoint supplies ordinary-language fixtures, independent artifact checkers, and the reviewed passive native runner for the [first supervision comparison](https://github.com/nisavid/provingkit/issues/336). The [contract](contract.md) proposes four native episodes. The retained evidence here ends at preparation and source review; it contains no native episode result or Jev assessment.

The two parser tasks distinguish runner discovery from legitimate repeat verification. The two report tasks share an initial CSV request and an amendment to JSON; the final message either requests sorting or explicitly restores CSV with the same sorting. All four remain ordinary-language tasks. The preflight uses only the discovery parser and the report sequence that retains JSON.

## Source and checks

- `ordinary-workloads/` holds agent-visible project seeds, prompts, and external reference checks. Its reference report implementation stays outside the evaluated project.
- `common-fixtures/` holds the independent parser and report artifact checkers and their local regression tests.
- `native-supervision/` holds preparation, passive hooks, receipt reconciliation, launch accounting, and bounded native transport.
- `native-supervision/integration/` retains package metadata, the lockfile, compiler configuration, and MIT license for [jev-axi a1fe619](https://github.com/nisavid/jev-axi/tree/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236). Its unchanged `src/` and `bin/` trees remain available at that immutable source link. Restore those trees under `integration/` before a fresh build. Third-party implementation copies, installed dependencies, and generated JavaScript are not duplicated here.

The prepared local candidate used an existing dependency installation and a successful TypeScript build. `integration-build.json` retains source hashes and that build result; the absolute compiler path is normalized. A fresh dependency installation or build needs a new manifest and verification before execution. `prepare.py` inventories the actual installed production dependencies and compiled files, binds their hashes and resolution paths, and creates four fresh attempts without starting a harness. `run.py` requires an accepted manifest digest and a coordinator receipt directory; its presence grants no execution authority.

The [workload checks](ordinary-workload-preparation-checks-v2.json) retain thirteen oracle tests, four reference report states, and seven parser seed/reference observations, including expected seed failures. The [runner checks](native-preflight-local-checks-v2.json) retain seven passing local tests and the four prepared manifests' initial checks. These are synthetic/local checks, not native results. Their public projections replace machine-local path prefixes and retain each original record's digest.

Both independent review focuses are clean on the same prepared revision: [source fidelity](fidelity-review.md) and [accounting](accounting-review.md). The [join](review-join.json) records their bindings and exact original-result digests. The accounting review's local citation prefix is normalized to this directory; otherwise the review prose is retained. Model selection is not effective-model attestation. [Source identities](source-identities.json) bind the published files and four local manifest digests.

The controller's Claude hook receipt parser follows the [official SDK lifecycle definitions](https://code.claude.com/docs/en/agent-sdk/typescript#sdkhookresponsemessage). Codex receipt definitions come from the locally generated 0.159.0 app-server schema. Actual compatibility with these CLI versions remains part of native qualification.

## Method and limits

The comparison consumes the unchanged `handling-sys1-incidents` intake aid; [the invocation record](protocol-procedure-consumption.json) binds its three files. These preparations add no shared skill convention.

The preflight omits both worker and Stop assessments while preserving original bookkeeping and observation preparation. The later comparison must settle its own shared Stop treatment. The preflight cannot demonstrate useful steering, a diagnostic consumer benefit, economic superiority, population reliability, or permission for a live change. Missing native failures or cadence-ten opportunities remain unqualified properties. After native inspection and accounting join, the full comparison contract remains to be accepted.
