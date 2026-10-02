# Provisional architecture evidence audit

I found no actionable evidence defect in the reviewed provisional packet. The source restrictions, frozen report identities, evidence limits, and retained implementation graph are consistent with the checked inputs. This is a preparatory evidence pass, not architecture acceptance, implementation qualification, or permission to begin delivery.

## Reviewed scope and decisions

The review covered the packet under `docs/superpowers/research/2026-10-01-repository-configuration/architecture/`, the published research synthesis and acceptance records, and the named immutable source. The 30 files present at the initial inventory stayed unchanged during this pass. The coordinator then added `architecture/README.md`; I read it and included it in the final 31-file identity inventory below.

Only the end-to-end GitHub capability and contextual-judgment answers in `operator-choices-1.json` are treated as accepted. Architecture, standalone Skill versus independent Plugin, live personal/public versus additional organization/private qualification, and all three local clients versus Codex-only remain pending actual human decisions. I supplied none of those answers.

The substantive source baseline is Provingkit commit `70879ae2ea94fac8708ab77051d08ded9429fce4`. Its changed paths relative to `02812cdee184023ecc06214e263c308d9131a1b0` are all in the published research directory; the projector and source validator are unchanged. Dotfiles source was read from commit `9e8000a7542203defcc58c5f23e883764f8fa405`. The local dotfiles HEAD was newer, `009f0afdb29ac1fd4575c1fc01b0b8867a2c684c`, but the five inspected dotfiles paths had no changes between those commits and no reported working-tree changes.

## Checks and results

### Packaging claims are supported at their stated revisions

- **The source validator checks exact directory membership.** `scripts/validate_provingkit.py:1589–1606` compares all directories immediately under `plugins/` with `EXPECTED_MEMBERS`, which names exactly the six current members. Its normal entry point calls that check at line 2415. A seventh directory would take the rejection branch. I inspected the source and statically extracted its member set; I did not create a seventh-directory fixture or run that rejection. The independent Plugin therefore needs a deliberate source/validation amendment if it uses that root. The conceptual ability to equip one Plugin is a separate fact. [Validator source](https://github.com/nisavid/provingkit/blob/70879ae2ea94fac8708ab77051d08ded9429fce4/scripts/validate_provingkit.py#L1589-L1606), [Kit definition](https://github.com/nisavid/provingkit/blob/70879ae2ea94fac8708ab77051d08ded9429fce4/release/provingkit/definition-v1.json#L18-L114).

- **The projector can select subsets of known members.** Its six-member policy supplies both the allowed names and default selection. `--slate` can select a known member; unknown names take the source rejection branch. Catalog name `provingkit` is hardcoded for all three targets. The packet correctly says an additional independent identity cannot use this operation unchanged; it does not confuse the whole-Kit release policy with an inability to project a known single member. [Selection and catalog construction](https://github.com/nisavid/provingkit/blob/70879ae2ea94fac8708ab77051d08ded9429fce4/scripts/build_release_artifacts.py#L146-L213).

- **The maintained dotfiles installer is specialized.** The source restricts member names, source repository, client routes/scopes, and marketplace names. Codex allows `provingkit` or `provingkit-local`; the other declared clients allow `provingkit`. Its maintained contract consumes pinned clean artifacts, separates materialization from client behavior, and documents the generic protected `agent-equipment apply` route as unavailable. That last statement is correctly a documented route limit, not an independent observation of every possible native tool. [Installer checks](https://github.com/nisavid/dotfiles/blob/9e8000a7542203defcc58c5f23e883764f8fa405/home/private_dot_local/bin/executable_provingkit-installations#L64-L150), [maintained contract](https://github.com/nisavid/dotfiles/blob/9e8000a7542203defcc58c5f23e883764f8fa405/docs/agent-equipment/provingkit-installations.md#L3-L11).

- **Reusable primitives do not establish a complete installation route.** The manifest, direct-child Skill discovery, and resource-containment helpers are independent of the six names. The Claude synchronizer creates links from already present shared Skills and skips occupied destinations; it does not acquire a Skill from Provingkit. The cited deployment test source constructs source-owned Skill copies and Claude links, but no test result for the proposed equipment is inferred. The packet leaves acquisition, one-source ownership, update/removal, and fresh invocation as work to define. [Generic primitives](https://github.com/nisavid/provingkit/blob/70879ae2ea94fac8708ab77051d08ded9429fce4/scripts/agent_plugins_standard.py#L87-L246), [Claude projection source](https://github.com/nisavid/dotfiles/blob/9e8000a7542203defcc58c5f23e883764f8fa405/home/run_after_sync-global-agent-skills-to-claude.zsh#L24-L48).

The Proseweaving example, six Plugin ownership introductions, preview source/projection contract, and marketplace-collision citation support the packet's narrower integration claims. They do not establish a current installation of the new procedure. All 21 immutable packaging citation path/range references resolve to local Git objects with valid line ranges, and I inspected their relevant content. Public URL accessibility was not tested.

### Frozen identity and exchange records are consistent

I recomputed every digest and byte count in `initial-reports.json`, `exchange-1.json`, and `cross-examined-reports.json`, plus the packaging report digest and common-brief/exchange cross-bindings. Every value matched. The common brief is `430c73eba6e5352bcca8b3668c3b1771d0cf8e0d257fa95d8be118df4cd430fb`; the exchange is `20796a6031b10f664d744f83fe3e08e1e188c53e28d90bad45eaa84ecff9d3b3`.

The retained accounts distinguish the three first proposals, two later variants isolated from peers, and common peer exchange. The variants explicitly record receiving the later operator choices; the first reports retain their earlier unresolved scope. The follow-ups acknowledge their peer exposure, retract the bespoke-actuator implication, and clarify that preparation does not impose another approval ceremony on an already authorized change. The final comparison describes convergence as design judgment, not independently measured success.

This verifies consistency of retained bytes and exposure accounts. I did not reconstruct private execution transcripts or attest that cooperative isolation was technically enforced. The method already states that limit.

I also verified all 55 entries of the published research candidate manifest, whose SHA-256 is `351a79780102e27bfd96285fd00b7d102c03ce11999be7da66a6a18b8d57dd5c`. That check confirms retained research identity; it does not repeat the original platform research or renew its date-bound claims.

### Proposed behavior remains separate from observations

The comparison, comparison cases, follow-ups, and packaging report identify paper traces as proposed behavior. They do not claim a behavior comparison, installed result, or hosted enforcement run. `coordinator-source-notes.json` reports launcher versions and explicitly says those reads do not prove equipment installation, discovery, invocation, or behavior. I did not rerun those launcher commands or independently verify their original stdout; no reviewed conclusion relies on treating the version report as client qualification.

The comparison preserves the frozen research's distinction between configured checks, executed coverage, and exercised enforcement. It also preserves the conflicting Copilot-documentation case without resolving it by assertion. This pass did not refresh external documentation or provider state.

### The initial implementation snapshot is internally consistent

All six body files in `implementation-map/index.json` match their listed SHA-256 values and the corresponding body strings in `initial-graph.json`. The retained snapshot lists children 375–379 in that order, all open and unassigned. Its child page and every blocker page report `hasNextPage: false`.

The index and snapshot contain the same dependencies: 375 and 376 each depend on 370 and 372; 377 depends on 375 and 376; 378 depends on 377; and 379 depends on 378. That explicit graph is acyclic. This is a check of the retained charting snapshot, not a read of current GitHub state.

The corrected bodies assign pre-deployment source/behavior obligations to implementation, published and installed identity to deployment, and useful fresh invocation to the final consumer. Later providers, broader contexts beyond the selected alpha, and a separate Provingkit-controls initiative sit outside the map's fog. Those changes address the two retained preparatory findings. The earlier review correctly says it did not accept the amended bytes.

The map makes delivery work explicit while retaining the present charting-only scope. Its first contracts remain contingent on the actual decisions carried by the design/context prerequisites. The new README labels the checkpoint provisional and directs readers to query the tracker for current state.

## Limits and required continuation

No actionable correction is requested by this evidence pass. The four human decisions and review of the resulting final candidate remain necessary for design acceptance. If the candidate or a relevant evidence dependency changes, refresh the affected part of this audit. After publication, independently verify the published bytes; this report does not establish publication.

No network request, live tracker read, provider experiment, installer invocation, fresh client session, behavioral evaluation, source edit, or Git/forge mutation ran. Only this audit report was written. Git checks found the named branch at the supplied baseline, no tracked/index changes, no active merge/cherry-pick/revert/rebase markers, and a non-shallow graph. The architecture directory was untracked. No upstream was configured, so no upstream-relative unpublished count was available. `git diff --check` was clean; a separate direct scan found no trailing whitespace in the candidate files. Relative Markdown destinations resolved. A host-path scan found only repository-relative dotfiles paths embedded in public source URLs, not machine-local path leakage.

## Readset and input identities

The coordinator's bounded audit brief, supplied workspace instructions, and ambient harness metadata were available. I used `research`, `codebase-design`, `capturing-agent-procedures`, and the read-only `checkpointing-and-publishing-git-work` route. A narrow memory-registry search returned no hits; no memory-derived evidence is used. I did not read historical transcripts.

In the following inventory, paths are relative to `docs/superpowers/research/2026-10-01-repository-configuration/architecture/`. Every file was hashed in full. I read the main comparison, method, README, brief, cases, manifests, choices, source notes, packaging report, all three cross-examinations, implementation files/snapshot, and preparatory review substantively. The frozen initial reports and two variants received whole-file content searches for source, qualification, and exposure claims plus bounded source/integration/exposure reads: minimal 91–115, flexible 105–130, caller 91–115, automation 60–80, and knowledge 77–105. That is an evidence-focused read, not a repeat of the conceptual architecture review. Truncated combined output was not treated as a complete read; relevant sections were reread separately.

### Provisional candidate inventory

| Path | Bytes | SHA-256 |
| --- | ---: | --- |
| `README.md` | 1556 | `d60628302237f1b4b0ba0a5a5930d7087ed5318ca744382b42b821c922fd4a86` |
| `automation-variant.md` | 14497 | `12f6c37595e95f979b9cfb9c705e4e15313c071ccd9c1fd0decaf8314d9c09c3` |
| `caller-cross-examination.md` | 15248 | `e95d1ed7f8052a458d17a5b1b925a4e3cf3605bcd98881292514079dec933bdb` |
| `caller-round-1.md` | 19300 | `4d62ef5fcb8dad81925c8cee11543f17d224b82199080e2186e0f9113c5890c6` |
| `common-brief.md` | 5844 | `430c73eba6e5352bcca8b3668c3b1771d0cf8e0d257fa95d8be118df4cd430fb` |
| `comparison-cases.json` | 3258 | `61a4caa4c8a253ae6c5745e68ad348266d2524352581342543e21a76ac7d938d` |
| `comparison.md` | 15644 | `420973ad70b7c07a429c588785560fa8f1940fb12822977901f5f0e837b7df0a` |
| `coordinator-source-notes.json` | 1227 | `a00bfc790f4f5437ada4b5987bc96bd4eabcdef0777f77ea722879734b5d405e` |
| `cross-examination.md` | 2976 | `5e1e3d507c77e0dcae85698282fdaf07dc0d7ae6b7bb052ac2094924b22b3764` |
| `cross-examined-reports.json` | 603 | `ceeaabb194493dc966e99ab9ce3a8cb6e37a73fd3c3596c206e7799ded561a03` |
| `exchange-1.json` | 1617 | `20796a6031b10f664d744f83fe3e08e1e188c53e28d90bad45eaa84ecff9d3b3` |
| `flexible-cross-examination.md` | 14678 | `a32f09f66cec028cfc8f0cc2655ccdcf412de9f396a8ad56de012a55d93b7fc4` |
| `flexible-round-1.md` | 20758 | `8c09acfa0b893010cfd1ba8284506381074b15546c95feae452f6b244904a487` |
| `implementation-map/consumer-invocation.md` | 1410 | `f347a38cca3919258717fb9ee10c7f3e538b3d661b3a8a16c5b5e1bbd2f2e66d` |
| `implementation-map/implementation.md` | 1999 | `964c4afba8cf813cda2c2247db766021b5de3fd182d75fbef78e8b191164ceeb` |
| `implementation-map/index.json` | 1163 | `7640677a237fef2783fe4531ff767ef59b61c9f14eaca1161cddca938e75e1e7` |
| `implementation-map/initial-graph.json` | 18682 | `3382c20428b0921299bb935afe4eaaaa6e1d2d08a37b735602dcfb052a817879` |
| `implementation-map/map.md` | 4390 | `70b4a34863cce6d1bae03d7b217fccc57144c848db232f026d9ab7e4c9ed4c8e` |
| `implementation-map/publication-deployment.md` | 1399 | `8de587045602595d566a00ff24ec2cf7d7cd4bf32a48cb9d27b7b895921da581` |
| `implementation-map/qualification-contract.md` | 2324 | `a64cd79887198337083f8b3f675705a76055ac5b9d862deb90dfe4cf327971c3` |
| `implementation-map/source-contract.md` | 1396 | `7d27e614a4e3fc8ab744ce4396eb4c8876f7cc79067e1ce4e5601d46397f5d67` |
| `initial-reports.json` | 743 | `66e09e01ad001888690dc4d00eb679797d7c144e7587b45e5523b1727fcda744` |
| `knowledge-variant.md` | 14294 | `0294cf93d8aa4be303832e4557e0f17bd49b3f67772e82c046b6d1cdb2184bc7` |
| `method.md` | 4686 | `128188862e6eec5702df10b8b07faca31f029d72f83c98d7d2096727ec7213fc` |
| `minimal-cross-examination.md` | 14064 | `23cb6893d914e7d6357a7e972f683c4d15544510736ec84799a79165fb7a659d` |
| `minimal-round-1.md` | 20267 | `9ea289b5fc91acfabf4e49466061c37ad0553c3a9fad59cba0cabe05947335b7` |
| `operator-capability-choice.json` | 1068 | `30f35c4e593f73e879182a4dab9b5af7e07d0d8c9ab9dcc6df722bdf77ce26a4` |
| `operator-choices-1.json` | 1530 | `7faee4d71242a99552752e04c5b6e80bc481dad27f97c6143007d7e901fc41c9` |
| `packaging-feasibility.md` | 15365 | `563c1feb380565ea0ad32fc6d1d8b9d46a7f347bd90e30575ddaa4bc8b9eb52b` |
| `packaging-report.json` | 228 | `61b1e9892e2ec795411e3bbadf6da973c88bfa86fd2684ad0c9adb7c5db0a101` |
| `reviews/implementation-route-preparatory.md` | 11700 | `4b50625a50a1f905bdd156fcc2d6f87a9b6f6ec130acbee804bc99c80a09e9aa` |

### Published research reads

The synthesis, method, and verification record were read substantively. The candidate manifest was parsed and all 55 named files were read for byte/size verification only; their complete byte-only readset is exactly the manifest below, not an implied substantive rereview.

| Path within the research directory | SHA-256 |
| --- | --- |
| `research-synthesis.md` | `c0673f9bd43f2ec756c825315afcdb50930043911974106c78928d544e1dff64` |
| `method.md` | `b679863bf23864be87a973d4c2c16343fa3b02780109b378591488cf8fece0fe` |
| `verification.md` | `a8b1a9b27c30298b4ed2ce66061acd12a10a5a1df6549d11b18004e1efeeeae9` |
| `reviews/research-candidate-1.json` | `351a79780102e27bfd96285fd00b7d102c03ce11999be7da66a6a18b8d57dd5c` |

### Immutable Provingkit source readset

All entries below use commit `70879ae2ea94fac8708ab77051d08ded9429fce4`. Ranges describe substantive inspection; hashes identify full files.

| Repo-relative path | Inspected content | SHA-256 |
| --- | --- | --- |
| `AGENTS.md` | full | `a6a42e796d9f1a63d5f701e755725fae92ae37592188389687252f5f81d34d8e` |
| `CONTEXT.md` | full | `7e9dac9fe2bdf9eec0e2cea0f7d3a23c042cbc53de3818b3aa6fced9ee085901` |
| `README.md` | 20–45 | `2c0c81d2e1e42b498b456f4cd86be258c47da1430b95ccfa1bffe0465450ff17` |
| `docs/agents/issue-tracker.md` | full | `e8bd5fbd8533fc07d769dd429dc6aa2a1bbf493f3097888d8d352d75ac42eb47` |
| `docs/agents/domain.md` | full | `7c4c9af286962ec10677275ab117d438dbdb1c7588f517d724a4e247c5f60d9e` |
| `scripts/validate_provingkit.py` | 1–95, 109–173, 1580–1620, 2413–2430; static member extraction | `163a61c97cfdfba2a153ac39e2d17fd46db2347068f99900ee436c24d2f3e93c` |
| `release/provingkit/definition-v1.json` | full | `c544e72895b5cdc20aac3633bb58a1be9eaf595f1a4571b7f8ea8e2b820ff965` |
| `release/artifact-projection-policy-v1.json` | 1–80 | `bca90965f36a60a46cae00c8d52c0d88db060f0d7cfa5f7b6c399b31b6c276ff` |
| `scripts/build_release_artifacts.py` | 1–230 | `1cc9aa7778c4fc82bca06c9b308d66fef873510690cbc304ed55afec35054917` |
| `scripts/agent_plugins_standard.py` | 1–260 | `2127db0cd06e8c6bc8185125d111930cc6abd76ca791cc844ce399dc48ca7a9e` |
| `plugins/proseweaving/README.md` | full | `3e3fcdc2a6deea752d9be9ecddc567ea5d3881395bc94090d401ab447b24000e` |
| `plugins/rolecasting/README.md` | 1–50 | `6e681db4e591b40a87fb129fb595dd7ac2ad8984f33614b12161c1cbf1996d19` |
| `plugins/tricritical/README.md` | 1–50 | `927b557154c762aeca47e25d93624d280fa75e1cd2d23bb85e5a0417cd0ef2a9` |
| `plugins/versionkeeping/README.md` | 1–50 | `a00f636a3d7ead47a10fb0eb65398ff34763dff25ef715fd3418ae51eee9062d` |
| `plugins/mergecraft/README.md` | 1–50 | `73e3b50b0be042b4abdf65cdcf604319c9933ef3e2618964a149b20eb78079bf` |
| `plugins/artifact-customs/README.md` | 1–50 | `bc0d961e6e916a7a3e3a56d7a7a239aad166a6369c233c011a61b5d3cc8f9755` |
| `docs/release-artifact-projection.md` | full | `cf9297a0dc1f592a535e047c9ea0596380ce8a1f90c7baa1e99a5725698d5243` |
| `docs/preview/install-and-update.md` | 1–48, 380–430 | `b476077b172e31474903c903f2718de81000e53f91f267ee27c50834bf30b9d8` |

### Immutable dotfiles source readset

All entries below are relative to `nisavid/dotfiles` at commit `9e8000a7542203defcc58c5f23e883764f8fa405`.

| Repo-relative path | Inspected content | SHA-256 |
| --- | --- | --- |
| `home/private_dot_local/bin/executable_provingkit-installations` | 1–160 | `70b36ea5396aeb48bdcd786746a2e58c3f1aaa592058f3c0fc8fd56570ef81d4` |
| `docs/agent-equipment/provingkit-installations.md` | 1–110 | `13bfe0662fbed4be5f0fc24de3e6344d43bd0da963180efb213d730095d1db2a` |
| `home/run_after_sync-global-agent-skills-to-claude.zsh` | full | `a66d1d8d74b2e1c20ac6b123834bb954a8343962e1ffb02c6b95a5b4944dca82` |
| `tests/public-agent-skills.zsh` | 594–637 | `d9ebf402aacc2cf2e5a22a25dd42c5ea25d65eb5d53bb5211d0efddaa81dd2df` |
| `home/dot_agents/skills/capturing-agent-procedures/SKILL.md` | full | `b9f13f1b78c338383253c1c89c79172d5f5e938757311c97569520e2ac6c7554` |

### Standing procedure readset

Each named procedure/resource was read in full. These identities record instructions consumed by this audit, not qualification of installed equipment.

| Skill/resource | SHA-256 |
| --- | --- |
| `research: SKILL.md` | `985569f15739c713d6784887c3d186d4ef9ac85bec5ad9c068d25bf0739928e4` |
| `codebase-design: SKILL.md` | `2c20617f87ec8af6a434859f381b2f061a69b530444e74eb39e78bb016a6d1e2` |
| `codebase-design: DESIGN-IT-TWICE.md` | `8e740bf98446dbd4dfdc132ac4346d9a7eedaf93de6a495889171cf7f99f16bd` |
| `codebase-design: DEEPENING.md` | `f3dd099ce99289bd213914d8ee3e2429b78309c3957ca4583f7659551b1d53c1` |
| `capturing-agent-procedures: SKILL.md` | `b9f13f1b78c338383253c1c89c79172d5f5e938757311c97569520e2ac6c7554` |
| `capturing-agent-procedures: references/producing.md` | `14171169d0184814ab0fed30c08b878bfbadcfa8bd0330fcb9079257d33120d6` |
| `Versionkeeping checkpointing-and-publishing-git-work: SKILL.md` | `cc01d6f851b1720ed94a8aa160e41ee8a2a4837f03c39d7642a9491e5596986c` |

The review completed on 2026-10-02 UTC against these inputs. Final acceptance must consume the recorded human choices and the final candidate.
