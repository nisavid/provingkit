# Receipt retention and landed checking: design inputs

This inventory identifies the source, runtime, and caller evidence needed to
finish [Design durable receipt retention and actual-landed-commit
checking](https://github.com/nisavid/provingkit/issues/136). It carries forward
the [accepted landing strategy](https://github.com/nisavid/provingkit/issues/132#issuecomment-5734437374)
and [accepted public interface](https://github.com/nisavid/provingkit/issues/135#issuecomment-5735195431)
at `c6cfb8392713b86573f3b86163aec3800dcbaed1`.

Status: ordinary engineering evidence and continuation requirements. Storage,
independent handoff, hosted observation, protected execution, and result
consumption still need a combined design, its required reviews, and the
operator's decision. No runtime, recovery, hosted, or security qualification is
claimed here. The companion [interface](receipt-correspondence-interface.md)
and [processor matrix](receipt-processor-compatibility.md) remain controlling.

## Accepted identities and retained materials

| Identity | Meaning and materials the design must make recoverable |
| --- | --- |
| B | Original comparison base. Preserve its complete committed inventory inputs so both B→H and B→C selections can be reproduced. B need not be an ancestor of H or C. |
| H | Reviewed head. Preserve its complete inventory and committed Receipt blobs, paths, modes, and binding metadata. |
| T | Observed pre-landing target. Preserve the commit and history needed to check the operation's landing relation and target freshness. T does not replace B. |
| C | Actual landed commit. Preserve the committed inventory, complete evaluated closure, and Receipts used by the final check. |
| S | Evaluated source. Preserve descriptor construction inputs, complete source closure, and processing inputs where the prepared method binds them through S. |
| P | Recorded reconciled processing revision. Preserve its processing source and matching runnable dependencies. Prepared Receipts have no separate recorded P. |
| D | Consumed procedure revisions, including the original producer's method and the checking method. Retain their full source and identify each role separately. |
| V | Maintained consumer implementation. Retain its source and manifest separately from the historical processor it invokes. |
| Additional source revisions | Retain every source revision that the historical check reopens, including a routing Receipt's original catalog revision described below. |
| External records | Preserve the full reviewed context, landing observation, H/C binding results, ordinary result, and separately required member results. Keep raw and canonical Receipt identities, manifests, failed grades, and lineage references. A digest cannot reconstruct missing inputs. |

Complete inventory inputs include the Slate definition, Rosters and topologies,
corpora, expectation and runtime-owner mappings, declared dependencies, fixtures,
projection declarations, and selected skill subtrees. Retaining only the selected
Receipt paths cannot reproduce selection. The final design must enumerate the
actual transitive inputs for every supported profile and method.

The public historical checks consume committed source and public Receipt
records. Original private observations retain their existing owners and access
obligations. This inventory neither imports them nor changes those obligations.

### Routing Receipts reopen another revision

The historical checker reads
`trigger.reconciliation.catalog.source_revision` through
`_check_routing_catalog` and `canonical_catalog`. That revision can be distinct
from S. Reconstructing its canonical catalog reads the Slate definition, each
member's topology, and every catalog skill entrypoint. A retention manifest
containing only the named B/H/T/C/S/P/D/V commits can therefore be incomplete.

This is a source-derived input requirement. It does not change the accepted
Receipt format or choose a storage mechanism. Qualification must include a
routing record whose catalog revision differs from S, removal of that revision,
and independent recovery of its exact source. See the immutable
[checker](https://github.com/nisavid/provingkit/blob/24c2d712a0be6a95958713ec80c7e06a89abdc6c/scripts/behavior_eval_receipts.py#L905-L915)
and [catalog reader](https://github.com/nisavid/provingkit/blob/24c2d712a0be6a95958713ec80c7e06a89abdc6c/scripts/behavior_eval_inventory.py#L610-L630).

## Historical runtime inventory

The named profiles are P957
`957550119aca20a31a26f4e5f9a3f09a2d6bd148` and P24
`24c2d712a0be6a95958713ec80c7e06a89abdc6c`. D079 is
`0797623a3d8dfafb600f0cb1009e4f6d4538bb30`; its five processing
files match P24 in bytes and committed modes.

| Surface | Source observation | Remaining evidence |
| --- | --- | --- |
| Python and platform | Both revisions' contribution guidance says CPython 3.13 or newer. Their CI selects Python 3.13 on `ubuntu-latest`. | Record and recover the exact qualified interpreter build, platform, and environment for each historical profile. A moving CI image and a minimum version do not supply that qualification. |
| Libraries | Receipt schema validation imports `jsonschema.Draft202012Validator`. CI installs `jsonschema==4.26.0`; the checker does not enforce that installed version. | Record the resolved dependency closure and retrievable distribution identities. No Receipt-specific dependency lock or complete environment manifest is present in either processor tree. |
| Other CI packages | CI also installs `idna` and `PyYAML`. The three Receipt Python modules do not directly import them. | Establish the actual runner's dependencies without treating every CI package as a Receipt dependency or ignoring transitive dependencies. |
| Source layout | Python modules use sibling imports and repository-relative schema and policy paths. Normalized processing binds five files; direct-core processing binds three. | Restore and verify the registered source manifest and layout. Reconciled legacy checks compare running bytes with P; their recorded Git modes are not checks of filesystem mode bits. |
| Git | The modules invoke `git` from PATH for commit resolution, committed blobs/trees, diffs without rename detection, and the historical ancestry check. | Record the qualified Git executable and necessary repository objects. The retained historical call uses S/S; the maintained correspondence check separately examines C. |
| Input shapes | Full lowercase 40- or 64-hex commit identities, normalized repository-relative paths, UTF-8 input, and regular Git modes `100644`/`100755` are expected. Inventory inspects selected validator ASTs for projection declarations. | Exercise both supported processor profiles and method shapes through their unchanged public entrypoints, including rejection cases. AST inspection is not validator execution. |

The [P24 contribution requirement](https://github.com/nisavid/provingkit/blob/24c2d712a0be6a95958713ec80c7e06a89abdc6c/CONTRIBUTING.md#L33-L39),
[CI declaration](https://github.com/nisavid/provingkit/blob/24c2d712a0be6a95958713ec80c7e06a89abdc6c/.github/workflows/provingkit-source.yml#L21-L40),
[schema and Git calls](https://github.com/nisavid/provingkit/blob/24c2d712a0be6a95958713ec80c7e06a89abdc6c/scripts/behavior_eval_receipts.py#L71-L139),
and [processing snapshot](https://github.com/nisavid/provingkit/blob/24c2d712a0be6a95958713ec80c7e06a89abdc6c/scripts/behavior_eval_receipts.py#L381-L396)
support these observations. Source inspection does not establish that a freshly
recovered environment can execute either profile. The accepted compatibility
matrix requires those measured results before activation.

## Reconciliation with the held caller proposal

The [Receipt implementation owner](https://github.com/nisavid/provingkit/issues/33)
and Proseweaving coordinator retain the earlier caller proposal and its review.
Both confirmed the document scope of this inventory. That earlier functional
review applies to its own proposal. The following differences must be resolved
in the combined design; this inventory does not silently adopt that proposal.

| Held proposal element | Accepted requirement to carry into the new caller |
| --- | --- |
| Two-input B/C comparison and checking | Supply the complete reviewed context and actual landing observation. Reproduce both B→H and B→C selection and verify the committed Receipt bindings at H and C independently. |
| S must be an ancestor of C | Execute the matching historical check at S/S, then compare the complete public closure at C. Preserve S's meaning through the rewrite. |
| T names a Receipt-only successor | Translate that historical role explicitly. In the accepted contract, T means the observed pre-landing target. The earlier Q/T/W corrective sequence is historical evidence, not a new normal sequence. |
| One future implementation root I | Identify V, the actual historical validation implementation, recorded P where present, prepared processing at S, and consumed producer/check D separately. |
| A reusable `workflow_call` entrypoint | Specify the independent pre-landing handoff, actual-C observation, delivery, interruption, and recovery mechanisms. A reusable entrypoint alone does not implement them. |
| Reachable commits and CI artifacts | Demonstrate independent recovery after ordinary branch cleanup and loss of transient copies. Current object reachability and artifact presence do not establish durable recoverability. |
| Aggregate check output | Preserve `pass`, `not-required`, `fail`, and `error`, raw identities, per-row diagnostics, and original failures. Preserve separate stricter member results and their consumer requirements. |

The proposed workflow and test paths in the held packet remain unallocated.
The existing source workflow, member validators, locks, projections, and shared
processor source remain with their owners. This document allocates no hosted
runs and changes no required checks, branch rules, or landing order.

## Evidence the combined design must make possible

These cases derive from the accepted contracts and the source inventory. They
define evidence to collect after the complete design and implementation exist;
they are not claims that the current caller implements the behavior.

| Case | Observation needed |
| --- | --- |
| Fresh recovery | Delete ordinary merged branches and remove transient/local copies; independently retrieve the complete source and runtime inputs, verify their identities, and execute every supported compatibility row. Include the separate routing catalog revision. |
| Missing material | Remove a required commit, source blob, processor, catalog input, or runtime dependency. Preserve the interface's distinction between missing provenance (`fail`) and unavailable historical runtime (`error`); neither qualifies. |
| Squash | Bind reviewed H and target T to the actual C; observe the accepted first-parent relation and full B→H/B→C comparisons. Unchanged evaluated closure may pass with S absent from C's ancestry. |
| Rebase | Obtain actual C and operation-specific history observations. The precise accepted relation and observation method still need the combined design; a constructed local rebase does not qualify hosted behavior. |
| Movement or changed selection | Move the target or change the selected consumers after review. Observe the accepted stale-context/selection failure rather than replacing B or reusing stale bindings. |
| Receipt-only range | Retain the original B when later commits contain only Receipts. An event-local empty comparison cannot qualify the earlier source change. |
| Committed bindings | Change H's Receipt while C/context agree; separately change C's Receipt. Observe distinct H/C failures. Dirty worktree files must not substitute for committed inputs. |
| Delivery and recovery | Omit delivery, repeat it, and interrupt checking or result publication. Demonstrate the eventual design's retry, reconciliation, and result-ownership rules; missing or incomplete results leave qualification pending. |
| External result | Bind the ordinary result to actual C, context, implementations, and procedures without another commit to C. Verify every selected row and preserve failures and diagnostic stages. |
| Member result | Observe ordinary quality 2/3 success alongside stricter 3/3 failure, and separately with that member result missing. The dependent member/readiness gate must remain unqualified. |

## Decisions and ownership still required

The combined proposal must settle:

1. Durable storage, retrieval, recovery, retention lifetime, and owner duties
   for the complete public material inventory and external records.
2. Independent context acquisition and handoff, event authenticity, and the
   operation-specific hosted observations for squash and rebase, including
   target freshness and forge races.
3. Matching historical runtime restoration and protected execution, with
   explicit unavailable-runtime behavior and no latest-processor substitution.
4. Missing, repeated, interrupted, and delayed delivery; recovery ownership;
   final result publication; and the consumer's validation of ordinary and
   separately required member results.

The security-dependent judgments in these decisions remain deferred to their
required model route. Ordinary source inventory and functional review cannot
accept them. The owning session must obtain a combined proposal with current
engineering and security reviews on the same final revision before asking the
operator to decide. Hosted/recovery evidence remains an activation prerequisite
after design acceptance.

Under `capturing-agent-procedures`, the Receipt implementation owner retains
`docs/behavior-eval-receipts.md` as the maintained method. The accepted caller
and recovery method must specify its inputs, owners, invocation conditions,
failure and recovery behavior, required outputs, and acceptance evidence there
or through a narrowly linked owned reference. Dependent producers, inventory
checks, member checks, callers, readiness, disclosure, and adoption must load
the reviewed published procedure, record D separately from processing, and
verify its required results before dependent execution can qualify. Procedure
capture and actual downstream invocation remain uncompleted.

[Owner migration](https://github.com/nisavid/provingkit/issues/137) still needs
this design and the accepted interface. This inventory supplies a continuation
input to the current owners; it does not initiate migration or activation.
