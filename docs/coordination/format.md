# Catalog format, version 1

The catalog command consumes one UTF-8 JSON object with `schema_version: 1`.
Top-level records are `snapshot`, `decisions`, `evidence`, `endpoints`,
`fabrics`, `profiles`, and `channels`. Optional `provenance` retains dated
crosswalks and inventory notes. IDs are readable lowercase words joined by
hyphens, unique within their record collection. References use those IDs.

## Snapshot and evidence

`snapshot` carries `revision`, `generated_at` (an ISO 8601 timestamp with a
timezone), and `coverage` (the actual coverage and outstanding reconciliation).
`decisions` contains reviewable decision URLs.

Each evidence record carries `id`, `kind`, `uri`, `observed_at`, `limits`,
and either a nonempty `revision` or a lowercase SHA-256 `sha256`. Kinds are
`source`, `synthetic`, `behavioral`, `live`, `review`, `release`, `deployment`,
and `decision`. A URI is an HTTPS pointer or a repository-relative file path.
Metadata validation establishes neither URI availability nor source truth.

## Endpoints and fabrics

Endpoints carry `id`, `name`, `host`, `surface`, `wave` (1–3), `evidence`,
and `limits`. Wave membership describes the delivery portfolio, not support.

Fabrics carry `id`, `name`, `role`, `status`, `parent` (ID or null),
`dependencies`, `crosswalk`, `evidence`, `source_scope`, `compatibility`,
`gaps`, `next_check`, and `effort`. Roles are `actuator`, `host`, `protocol`,
`router`, `observer`, `presentation`, `trigger`, and `support`. Status is
`discovered` or `unsuitable`; unsuitable records require a specific gap/reason.
Parent and dependency edges must be acyclic. A composition names its component
dependencies; a component's evidence does not qualify their combination.

`provenance.component_dependencies.reconciliation` retains the finite
source-to-component audit for a batch. Its records identify the fabric,
source crosswalk, mandatory component IDs, alternatives, grouping-only
relation, unresolved binding, and evidence rationale. A full seed covers every
fabric; later batches preserve unrelated records and reconsider affected
dependents. Required component classes with unresolved exact identities use
explicit `support` fabric records with binding gaps. Their dependencies express
source requirements, never installed instances or operation success. This
provenance is reviewed against producer evidence; the command does not certify
its semantic completeness.

`compatibility` carries `status` (`unassessed`, `assessed`, `incompatible`,
or `mixed`), a behavior-specific `scope`, and `evidence`. Assessed or
incompatible status requires evidence. Include carry-forward rationale and
affected functions in `scope`, citing the supporting assessment.
`effort` carries `active_minutes` (a nonnegative number or null) and `cost`
(an observed cost description or null). Unknown values stay null.

## Profiles and operation claims

Profiles carry `id`, `fabric`, `channel` (ID or null), `population`
(`existing` or `controlled`), `ownership`, `relationship`, `target_input`
(`exact-reference` or `creation-contract`), `input_semantics`, `consent`,
`continuity`, `assurance`, `claims`, `gaps`, and `next_check`.
`consent` has `references` and `limits`; these describe applicable decisions
and missing verification, rather than granting permission.
`continuity` carries explicit `idle`, `busy`, and `restart` descriptions.
An existing-task profile uses an exact reference. Controlled profiles may
use a creation contract or an exact reference for their later operations.

Each claim carries `operation`, `milestone`, `stage`, `coverage`, `evidence`,
and `limits`. The command's operation vocabulary is:

| Operation | Milestones |
| --- | --- |
| `notify` | `submitted`, `receipt`, `acknowledged` |
| `request-work` | `submitted`, `receipt`, `accepted`, `executing`, `output`, `fulfilled` |
| `create-task` | `submitted`, `addressable`, `executing` |
| `inspect` | `status`, `result` |
| `reply` | `synchronous-return`, `later-reply` |
| `continue-task` | `submitted`, `same-task-context`, `replacement`, `fork` |

Stages are `discovered`, `source-assessed`, `prototyped`, `selected`,
`implemented`, `qualified`, `released`, and `deployed`. Coverage is
`unknown`, `partial`, `declared`, `proved`, `unsuitable`, or `inapplicable`.
Every claim has evidence and explicit limits. A `qualified` claim requires
live evidence and a named channel; `released` and `deployed` require release
and deployment evidence respectively and a named channel. Shared profiles
with `channel: null` cannot carry these stages. This check cannot determine
whether the live evidence actually proves target binding or the milestone.

Each operation claim may carry optional `outcome`, which preserves `queued`, `held`, `refused`, `stale`,
`incomplete`, or `unknown` separately from proved stages. Each profile may carry optional
`source_assessment`, which retains the comparison's dated six-position `vector`,
`evidence`, and original `limits`. It does not establish the confirmed positive
outcome. Receipt, acknowledgment, output, validated fulfillment, synchronous
return, later reply, same-task continuation, and replacement remain separate
claims. A profile with no claim for an operation leaves it explicitly unknown
in the view.

The archived vector uses exactly six positions from `S`, `P`, `?`, `U`, and
`–`, following its retained legend. ASCII `-` and symbols from other report
legends are rejected rather than silently reinterpreted.

## Channels and projections

Channels carry `id`, `source`, `target`, `fabrics`, `profiles`, `caller_access`,
`target_binding`, `evidence`, `gaps`, and `next_check`. Only one channel record
per ordered endpoint pair is supported. Self-pairs belong to separate control
experiments. Every linked profile's fabric must be listed; a channel-bound
profile can appear only in that channel. A shared source profile adds source
assessment and its limits, rather than qualified directional evidence.

`project` creates potential ordered pairs over the endpoint inventory,
including directions with no association and therefore no inferred candidate.
It emits a SHA-256 of its exact input bytes, the supplied snapshot metadata,
the canonical operation/milestone vocabulary, nodes/arcs, matrix cells, shared
channel details, and all fabric/profile/evidence records. Sorting is stable;
`--through-wave N` limits navigation to endpoints in waves 1 through N while
keeping supporting fabric and evidence records available.

Projection supports at most 64 selected endpoints and selected endpoint IDs of
at most 256 characters. These checks run before ordered-pair allocation: a
64-endpoint view has 4,032 directed channels and 4,096 matrix cells. A wave
filter can select a supported subset of a larger catalog. Metadata validation
can accept an inventory that exceeds projection capacity; `project` then
returns a named diagnostic, exit status 1, and no partial view. These working
limits do not exclude fabrics or discard directions within an admitted view.
If reconciled required coverage exceeds them, revise the capacity design before
claiming a complete view.

Intake is limited to 8 MiB. Output uses JSON escapes so admitted free text,
including escaped surrogate values, can round-trip through strict UTF-8 output.
These metadata and navigation bounds establish no hostile-input isolation or
live harness capability.

These records describe capabilities and evidence. Tracker state and authority
remain with their owning decisions and native graph.
