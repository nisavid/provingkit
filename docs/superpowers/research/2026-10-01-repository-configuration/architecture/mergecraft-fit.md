# Repository configuration in Mergecraft

One repository-configuration Skill fits Mergecraft, provided Mergecraft's stated responsibility expands to include GitHub repository configuration. I recommend that placement for the selected focused-Skill design. The current source does not already provide this capability: the change adds a distinct user intent and its implementation rather than reclassifying an existing PR workflow.

This assessment uses immutable repository objects from commit `358df580f6467c75808510368fd7cad9ac77f2ad`. It is a source and design assessment, not behavioral qualification, installed-client discovery evidence, or authorization to change a repository. The coordinator separately owns comparison with current remote source. I did not inspect the earlier architecture variants, comparison, or packaging reports.

## Why this fits, and what must change

Mergecraft already extends beyond merging. Its README assigns GitHub Issue and PR body authoring, Issue–PR contributions, publication, feedback, readiness, and stacked fixups to the Plugin. Its topology also represents ordinary GitHub reads and writes without requiring a custom helper for every operation. This supplies an existing place for forge-facing agent equipment and composition with Git work and PR publication. [Mergecraft README, lines 3–43 and 138–159](https://github.com/nisavid/provingkit/blob/358df580f6467c75808510368fd7cad9ac77f2ad/plugins/mergecraft/README.md#L3)

The fit is an intentional expansion. The canonical manifest describes Issue–PR relations and the PR lifecycle; the root entrypoint and design-principles responsibility table are narrower still. None lists repository creation, general settings assessment, configuration defaults, or prospective CI hardening. Those declarations should change alongside the new Skill so callers can discover its full purpose. Calling the work merely another merge gate would leave accepted capabilities outside the declared responsibility. [Canonical manifest](https://github.com/nisavid/provingkit/blob/358df580f6467c75808510368fd7cad9ac77f2ad/plugins/mergecraft/plugin.json), [root entrypoint](https://github.com/nisavid/provingkit/blob/358df580f6467c75808510368fd7cad9ac77f2ad/README.md#L22), [design principles, lines 35–60](https://github.com/nisavid/provingkit/blob/358df580f6467c75808510368fd7cad9ac77f2ad/docs/plugin-system/design-principles.md#L35)

The new public interface should accept the requested repository outcome, supplied context and policy, observed repository state, and the work already authorized. It should cover creating a repository, assessing existing configuration, selecting defaults, making a focused change, and hardening CI, including authorized application. These are useful direct invocations of one configuration concern. They do not need separate public Skills or separate workflow layers.

The depth comes from hiding repeated discovery and reasoning: determining which settings apply, distinguishing repository settings from inherited policy, looking up current provider support, identifying interacting choices, applying the selected change, and checking its effect. Source-linked guides and selective helpers can sit behind that interface. The caller should not have to learn a second configuration registry before asking for an informed change.

This matches the selected architecture recorded in `operator-choices-2.json`: one focused Skill, concise source-linked guides, existing native tools, and selective helpers for recurring mechanical risks. Its SHA-256 at the read used here was `72e8188856dbfe1abba0e462e41333f8ba846da0e17df000b1b745a9bd4082d8`. The coordinator's subsequent brief adds personal/public and organization/private live qualification contexts and all three local clients. Those are future qualification requirements, not observed results in this assessment.

## Responsibility and composition

| Concern | Current source | Proposed composition |
| --- | --- | --- |
| Repository creation, defaults, configuration assessment, and focused settings changes | No current public Skill trigger or operation owner covers this whole concern. | The new Skill owns the configuration decision and its authorized application through available native tools. |
| CI hardening | The existing CI adapter diagnoses a bound GitHub Actions failure and permits only the scoped repair or rerun authorized for that failure. | The new Skill owns prospective configuration hardening. Use the existing adapter when the actual task is its diagnosed-failure case; do not stretch that adapter to cover general hardening. |
| Committing and pushing workflow or repository files | Versionkeeping owns Git/index/ref/push mechanics and local integration. | Keep configuration and file-content judgment with the new Skill; invoke Versionkeeping when the outcome requires checkpoints or publication. A native setting change need not acquire a Git workflow. |
| Creating or editing a PR to deliver configuration files | Mergecraft's PR publisher owns exact PR creation, content, and readiness operations. | Invoke it when a PR is actually needed. Repository settings changes do not become PR publication operations. |
| Issue–PR associations and cached closure settings | Relation maintenance qualifies contributions and reconciles authorized relation effects; ordinary relation handling does not change settings. | Leave relationship maintenance there. A settings change belongs to the new Skill; a known change that affects a cached observation must invalidate that observation under the existing relation contract. |
| Security consequences | General review is owned by Tricritical; distinct security scrutiny is consequence-triggered specialist work. | Configuration work may use an appropriate security specialist for a concrete uncertainty or review focus. Do not make every routine configuration choice a separate security approval workflow. |

The first four rows are grounded in the public roster and topology, the [CI adapter](https://github.com/nisavid/provingkit/blob/358df580f6467c75808510368fd7cad9ac77f2ad/plugins/mergecraft/skills/getting-prs-merged/references/gh-fix-ci-adapter.md), [Versionkeeping's responsibility](https://github.com/nisavid/provingkit/blob/358df580f6467c75808510368fd7cad9ac77f2ad/plugins/versionkeeping/README.md#L3), and the [PR publisher's routing](https://github.com/nisavid/provingkit/blob/358df580f6467c75808510368fd7cad9ac77f2ad/plugins/mergecraft/skills/publishing-reviewable-prs/SKILL.md#L8). Relation behavior is documented in the [Mergecraft README, lines 45–69](https://github.com/nisavid/provingkit/blob/358df580f6467c75808510368fd7cad9ac77f2ad/plugins/mergecraft/README.md#L45) and its [Skill](https://github.com/nisavid/provingkit/blob/358df580f6467c75808510368fd7cad9ac77f2ad/plugins/mergecraft/skills/maintaining-issue-pr-relations/SKILL.md). Specialist composition follows [the design principles, lines 83–121 and 144–150](https://github.com/nisavid/provingkit/blob/358df580f6467c75808510368fd7cad9ac77f2ad/docs/plugin-system/design-principles.md#L83).

There is no necessary ownership collision if the new Skill keeps this interface. A collision would arise if it copied Git publication, replaced PR publication, or treated broad repository hardening as permission to alter whatever blocked a merge. A changed configuration observation may also make a consumer's earlier evidence stale. That is an actual dependency to preserve, not a reason to introduce a universal configuration approval layer.

The new Skill should support context-sensitive, informed choices beyond the settings discussed in its guides. The applicability limits are actual policy, task authority, provider support, unresolved consequential ambiguity, and concrete harm. An uncataloged setting is a prompt to investigate current documentation and context; it is not by itself an unsupported operation.

## Mergecraft versus a separate distribution

| Placement | What it gains | What it costs |
| --- | --- | --- |
| One new Skill in Mergecraft | Reuses the existing forge-facing Plugin, native client projections, validation route, and nearby workflow owners. Callers discover one additional focused Skill. | Requires a truthful scope expansion and shares Mergecraft's content identity and release cadence. |
| A standalone Skill | Gives configuration a visibly separate source and potentially its own update cadence. | Needs its own maintained discovery and delivery route for the selected clients, while still composing with the same Git and PR owners. The existing Plugin projector does not supply a standalone-Skill artifact route. |
| An independent Plugin | Gives repository configuration an independent member identity and deployment choice. | Adds a manifest, projections, validation, release registration, and distribution decisions for one Skill. Including it in Provingkit would also change the Slate; keeping it outside the Kit needs a distinct distribution route. |

The current need does not demonstrate independent lifecycle or deployment requirements strong enough to justify the extra distribution. One Skill remains a small caller interface inside Mergecraft, so sharing a Plugin does not require callers to use the other Skills. Reconsider separate distribution if configuration develops an independently useful release cadence, audience, or installation requirement. General repository configuration can stand on its own conceptually; that alone does not require another Plugin.

The release distinction is source-backed: Plugins are independently releasable members, the current Slate is explicit, and the projector selects Plugin identities from that Slate. These facts establish the integration work, not a prohibition against adding another Plugin. [Release contract](https://github.com/nisavid/provingkit/blob/358df580f6467c75808510368fd7cad9ac77f2ad/docs/release-boundary.md#L7), [projection policy](https://github.com/nisavid/provingkit/blob/358df580f6467c75808510368fd7cad9ac77f2ad/release/artifact-projection-policy-v1.json), [projector, lines 146–179](https://github.com/nisavid/provingkit/blob/358df580f6467c75808510368fd7cad9ac77f2ad/scripts/build_release_artifacts.py#L146)

## Smallest coherent source amendment

1. Add one direct-child Skill beneath `plugins/mergecraft/skills/`, with its `SKILL.md`, client interface metadata, focused source-linked references, and only the helpers justified by recurring mechanical risk. A name such as `configuring-repositories` is a proposal, not an accepted name.
2. Extend Mergecraft's canonical manifest and generated Claude adapter, its README and public roster, the root human entrypoint, the design-principles responsibility description, and its changelog. A concise responsibility statement is “GitHub repository configuration, Issue and pull-request authoring, and the pull-request lifecycle.”
3. Add the Skill's public contract and actual calls to `topology.json`; update the validator's finite public roster, file inventory, interface prompts, applicable assertions, and the README operation projection. Declare configuration ownership at the useful workflow seam. Do not expand this into an exhaustive per-setting catalog or require custom actuators for native changes.
4. Add focused behavior and discovery evaluations, meaningful helper tests where helpers exist, and the source validation appropriate to the new contract. Cover both ordinary informed execution and cases where actual policy or unresolved consequential ambiguity changes the result. Verify that create, assess, defaults, focused change, and CI hardening remain reachable through the single interface.
5. Refresh affected evidence, then the ordinary Mergecraft content lock through its documented writer. Run Mergecraft validation, its relevant tests, source-skill disposition validation, and diff checks. Preserve unrelated source and existing evidence whose dependencies remain unchanged.

These are normal contract additions. The current validator rejects a new directory until `PUBLIC_SKILLS`, declared inventory, topology, and interface metadata agree; that is a maintained-source requirement, not a reason to narrow the Skill's native-tool judgment. It explicitly accepts ordinary-tool operation dispositions. [Validator, lines 77–97, 2000–2130, and 2507–2631](https://github.com/nisavid/provingkit/blob/358df580f6467c75808510368fd7cad9ac77f2ad/scripts/validate_mergecraft.py#L77)

No new topology schema version is demonstrated necessary merely to add a Skill using the current shape. No new MCP server, configuration broker, public router, or generalized executor is justified by this assessment.

## Target and release implications

The existing projection policy already includes `skills/**` for Agent Plugins/Codex, Claude Code, and Cursor. The new Skill and its permitted resources should therefore follow those routes once the Plugin candidate is updated. The projector generates Cursor's manifest and excludes development topology, evals, and content locks from runtime artifacts. The Skill's executable instructions and resources must remain usable without relying on those excluded support artifacts. This is a source-level projection conclusion; I did not build or load a new candidate. [Projection policy](https://github.com/nisavid/provingkit/blob/358df580f6467c75808510368fd7cad9ac77f2ad/release/artifact-projection-policy-v1.json), [projector, lines 90–96 and 167–213](https://github.com/nisavid/provingkit/blob/358df580f6467c75808510368fd7cad9ac77f2ad/scripts/build_release_artifacts.py#L90)

Adding the Skill changes Mergecraft's governed content identity. Its current content-lock calculation includes Plugin files other than `CHANGELOG.md` and `LICENSE`, including the Skill, manifests, README, and topology. Qualification and release work must bind to the resulting candidate and refresh evidence affected by that change. This does not mean every unrelated historical behavioral observation must be rerun. [Content-lock source](https://github.com/nisavid/provingkit/blob/358df580f6467c75808510368fd7cad9ac77f2ad/scripts/validate_mergecraft.py#L5280)

The inspected canonical Mergecraft manifest says `1.0.0`. This is not evidence of a currently installed or publicly released version. The next alpha or preview must select and record its own candidate identity under the release contract; I do not infer an alpha number from a cached Plugin. Existing pinned preview artifacts do not change when source changes. Source validation, artifact projection, client qualification, publication, and deployment remain distinct claims. [Release contract, lines 22–57](https://github.com/nisavid/provingkit/blob/358df580f6467c75808510368fd7cad9ac77f2ad/docs/release-boundary.md#L22)

The implementation map should carry the selected personal/public and organization/private contexts and all three clients into later qualification work, with concrete fixtures and client surfaces specified there. Neither those selections nor this placement recommendation establishes runtime success or starts that work.

## Remaining operator choice

The user has suggested Mergecraft as the home, and this assessment supports carrying that direction into the implementation map. I recommend one new Skill there with the stated scope expansion. That is a source-grounded design judgment in response to the suggestion, not evidence of a separate checkbox acceptance. No additional operator decision is required merely by the Plugin packaging.

Any remaining choices should concern actual consequences not yet settled: a separately desired distribution lifecycle, the source channel and candidate selected for publication, or concrete live qualification fixtures where those remain unspecified. The coordinator can record those in the corresponding map contracts. A per-setting catalog, extra actuator, or new safety approval is not a packaging choice to put back to the user.

This handback completes only the requested source assessment. No tracked source, tracker, live repository setting, release artifact, or installed client was changed.

## Evidence inventory

Every repository content read below used `git show 358df580f6467c75808510368fd7cad9ac77f2ad:<path>`; later line selections and JSON projections came from those same immutable Git objects. The commit identity was fixed before reading, so this inventory does not substitute later hashes of mutable paths for initial identities.

| Source path | Read scope |
| --- | --- |
| `AGENTS.md` | Complete. |
| `CONTEXT.md` | Complete. |
| `README.md` | Mergecraft references and two lines of surrounding context. |
| `plugins/mergecraft/plugin.json` | Complete. |
| `plugins/mergecraft/.claude-plugin/plugin.json` | Complete. |
| `plugins/mergecraft/README.md` | Complete, with bounded rereads after aggregate output truncation. |
| `plugins/mergecraft/topology.json` | Lines 1–220; projected contracts/calls/operations for publication, resume, and merge; final 16 ordinary-tool operations; all name, trigger, and conditional-call matches plus selected operation matches. |
| `plugins/mergecraft/skills/maintaining-issue-pr-relations/SKILL.md` | Complete. |
| `plugins/mergecraft/skills/publishing-reviewable-prs/SKILL.md` | Lines 1–130. |
| `plugins/mergecraft/skills/getting-prs-merged/references/gh-fix-ci-adapter.md` | Complete. |
| `plugins/mergecraft/CHANGELOG.md` | Complete (requested lines 1–80). |
| `plugins/versionkeeping/README.md` | Complete (requested lines 1–125). |
| `scripts/validate_mergecraft.py` | Matching lines for roster, operation, manifest, topology, version, evidence, source-stage, and validation symbols; lines 35–165, 2000–2140, 2507–2635, 5270–5319, 5470–5505, and 5612–5675. |
| `release/plugin-content-locks/mergecraft.json` | Lines 1–12. |
| `docs/plugin-system/design-principles.md` | Lines 1–155. |
| `docs/release-boundary.md` | Complete (requested lines 1–220). |
| `docs/release-artifact-projection.md` | Complete (requested lines 1–150). |
| `release/artifact-projection-policy-v1.json` | Complete. |
| `scripts/build_release_artifacts.py` | Matching lines for member/projection-related symbols; lines 65–110 and 130–218. |

Tree-name inventory covered the Mergecraft and Versionkeeping Plugins, release paths, and repository docs. The attempted `plugins/mergecraft/.codex-plugin/plugin.json` read found no object at this commit; it supplied no content evidence. I did not read the earlier architecture reports discovered in the tree inventory.

Additional inputs were read and hashed together in the same operation:

| Input | SHA-256 |
| --- | --- |
| Installed `codebase-design/SKILL.md` | `2c20617f87ec8af6a434859f381b2f061a69b530444e74eb39e78bb016a6d1e2` |
| Installed `capturing-agent-procedures/SKILL.md` | `b9f13f1b78c338383253c1c89c79172d5f5e938757311c97569520e2ac6c7554` |
| Cached `versionkeeping/0.1.0-alpha.3/skills/checkpointing-and-publishing-git-work/SKILL.md` | `cc01d6f851b1720ed94a8aa160e41ee8a2a4837f03c39d7642a9491e5596986c` |
| `docs/superpowers/research/2026-10-01-repository-configuration/architecture/operator-choices-2.json` | `72e8188856dbfe1abba0e462e41333f8ba846da0e17df000b1b745a9bd4082d8` |

The installed codebase-design and capture instructions were initially read without a digest, then reread with the hashes above; those hashes identify the second reads. Installed Skill paths establish instruction provenance only, not runtime qualification. A narrow memory-registry search returned no relevant hits and supplied no factual basis.

Read-only Git observations: branch `nisavid/research/repository-configuration`; HEAD `358df580f6467c75808510368fd7cad9ac77f2ad`; no configured upstream; local remote-tracking ref `origin/nisavid/research/repository-configuration` had the same commit; no observed merge, rebase, or cherry-pick operation. The operator-choice JSON files were untracked coordinator work and were left untouched. I did not fetch, commit, push, invoke publication planning, run Plugin validators, build an artifact, or exercise live configuration behavior.
