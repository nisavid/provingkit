# Host-preservation admission at capture time

This contract binds a preservation validation request to an observation checked
by the deployment owner. A successful consumer result establishes correspondence
to that observation at its recorded capture time. Current applicability requires
a new check with the deployment owner before use.

The selected method is an owner-reviewed, request-bound snapshot. This maintained
source prepares that method for the Mergecraft-only delivery validator. The
[record schema](../release/host-preservation-admission/record.schema.json) has
identity `provingkit-host-preservation-admission-prepared-v1` and requires
`contract_status: prepared-not-adopted`. Its shape checks provide no actual
baseline admission. The production producer, semantic validator, and hosted
caller adapter remain unimplemented by this contract.

[Host rollout maintenance](https://github.com/nisavid/provingkit/issues/139)
owns deployment evidence and its acceptance. Source preparation leaves the
installed selection, recovery material, and agreed installation route intact.
Installation, public evidence transfer, signing, and qualification retain their
separate decisions and evidence.

## Record and ownership

The deployment owner retains the private baseline, immutable decision history,
and a replaceable pointer to the history's head. The repository-configuration
owner consumes the deployment owner's return and owns the delivery validator.
Dotfiles owns the installation-view exporter and its inner schema.

The schema has two disjoint, closed branches: a complete observation record and
an explicitly nonpassing response. The following fields describe the complete
observation. A complete shape still requires the semantic checks below before
any correspondence result.

| Record field | Meaning |
| --- | --- |
| `record_origin` | `constructed` for test data or `owner-reported` for a supplied owner observation; neither label authenticates its author. |
| `producer_contract` | Exact reviewed producer-contract bytes consumed for this request. |
| `subject` | Development and delivery commits, Mergecraft as the changed member, the other five preserved members, and the selected route contract. |
| `baseline` | All Kit members, client observations, shared state, and required preservation coverage. |
| `exports` | Exact exporter records plus their complete inventory, receipt, selection, and mode identities. |
| `owner_decision` | Original decision evidence and the baseline, subject, exports, and producer revision it covers. |
| `currentness` | The request-bound observation of the maintained decision source and its head. |
| `public_transfer` | A separately governed public-projection branch; `not-selected` keeps the hosted path unavailable. |
| `claim` | `correspondence-to-owner-admitted-observation-at-capture`. |

Each file reference carries a logical name, exact byte count, and SHA-256.
Logical names resolve through a separately frozen input map. They supply no
filesystem access or network instructions. The outer record has no embedded
self-digest: the owner supplies its digest separately through the private
return channel.

`subject.record` and `baseline.record` identify raw files containing only the
respective statement. Each supplied `statement` must equal the strict parse of
those exact raw bytes. This arrangement avoids self-digest cycles.

The inner exporter remains `provingkit-installation-view-export-v1`, with schema
SHA-256 `5e336e23d8231a7b04ad0de2d4ac4e430200cf23c8a0f6df393b64062ce9af86`,
from dotfiles commit `e463260bd6879fb41d2cb977075ac70ae8f5fc6c`. This contract
references it without changing it. Consumers load the exporter procedure from
its independently reviewed source before processing its records. An archive
digest described by that exporter as declared remains declared here.

## Missing or unavailable evidence

When a required identity is unknown, return the nonpassing branch. It retains
the exact `admission_request`, independently reviewed `reviewed_contract`,
`observed_at`, and available file identities in `known_records`. Its
`dependencies` entries name each missing or unavailable dependency and give a
reason. They describe missing evidence without supplying a fabricated byte
count or hash. The response also requires an overall `reason` and an `outcome`
of `missing-evidence` or `unavailable`.

This branch fixes `claim` to `no-preservation-correspondence`. It carries no
complete owner decision or `currentness` object and cannot claim a matching
observation. Keep a known expected identity in `known_records` when the file
itself is inaccessible; describe the access failure in `dependencies`.
Preserving known identities is a semantic requirement beyond schema syntax.

Both branches use the same prepared schema identity and status. Validate the
selected branch before interpreting its outcome; a malformed or mixed response
is a contradiction. A well-formed nonpassing response keeps its declared
missing/unavailable outcome, subject to consistent reasons and dependency
states. Obtaining the missing evidence later requires a new complete observation
and owner return, rather than upgrading the old response. If the immutable
request or reviewed contract cannot be identified, stop before constructing a
bound response and report that prerequisite through the owner channel.

## Preservation coverage

The baseline covers Rolecasting, Tricritical, Versionkeeping, Mergecraft,
Artifact Customs, and Proseweaving. Mergecraft is the only changed member.
For the other members, the consumer compares projected bytes, file and directory
modes, versions, relevant enabled and registration state, shared catalog fields,
and recovery evidence. The selected route contract defines permitted changes
to registration and load paths. A partial member inventory cannot satisfy this
contract.

Codex and Claude Code are preservation subjects and proposed execution clients.
Those labels grant no execution authority. Cursor is preservation-only. Its
observations record either measured coverage or `unavailable` with a reason.
Unavailable evidence cannot satisfy required client or member coverage, establish
Cursor readiness, or pass an all-client preservation claim.

## Owner decisions and renewal

An acceptance decision binds the exact raw baseline and subject statements,
export records, reviewed producer contract, declared claim, and original deciding
owner's evidence. `accept-for-preservation-validation` is the only decision kind
that can support acceptance. A withdrawal identifies the affected prior decision;
a supersession identifies both that decision and its successor in the maintained
history. Preserve prior record bytes when replacing the head pointer.

For every new consumer request, the deployment owner reobserves the decision
source, its head, and all bound material dependencies. The return binds the
immutable request, observation time, and observed head identity. A changed source,
artifact, producer, route, or required coverage needs renewed evidence. Missing,
inaccessible, conflicting, withdrawn, or superseded inputs produce a nonpassing
return. A producer declaration or candidate-supplied acceptance flag cannot
replace original owner evidence.

Head reads are cooperative observations. They provide no atomic or adversarial
guarantee. The snapshot cannot establish the absence of a withdrawal after
capture. There is no fixed TTL or unattended lease. Repeating an offline check
can establish historical correspondence to the same observation; current
applicability requires reentry to the deployment owner.

## Prepare and consume a request

Agents use `capturing-agent-procedures` and load this document at its reviewed
revision when preparing preservation inputs, renewing an observation after a
material change, or resolving withdrawal or supersession. Ordinary installation
work continues through its separately selected installation procedure.

1. Freeze the claim, route, complete member identities, development and delivery
   commits, required coverage, consumer request bytes, input map, reviewed
   contract identity, and original owner-decision evidence. Missing inputs remain
   explicit missing evidence in the nonpassing branch. The immutable request
   and reviewed-contract identities are prerequisites for either branch.
2. Consume the exact raw subject and baseline statements, full export records,
   inventories, both raw receipts, and mode evidence. Verify bytes and digests
   before parsing and identities after consumption. Reject duplicate JSON keys,
   nonfinite numbers, malformed encodings, incomplete reads, ambiguous names,
   and unresolved file-identity changes.
3. Check the prepared record's shape, the unchanged inner exporter schema, raw
   statement equality, complete preservation coverage, and cross-record bindings.
   JSON Schema alone cannot complete this step's semantic checks.
4. Obtain a new request-bound observation from the deployment owner. Consume the
   maintained decision history, original decision evidence, observed head, and
   current material dependencies. Return an explicit nonpassing outcome for an
   unavailable decision source or any failed binding.
5. Receive the raw complete record or nonpassing response, its digest, reviewed
   contract identity, request identity, and head identity when observed through
   the private owner channel.
   The consumer obtains the expected digest and contract identity independently
   of its candidate packet and compares them before interpretation.
6. Report the outcome and its capture-time limit. Retain the raw inputs,
   actual owner return, comparison results, and source revision. A new operation
   requiring current applicability returns to step 1 with the owner.

For an Actions caller, pin the independently accepted admission manifest and
workflow/request revision. Values supplied by the candidate PR cannot admit
that same candidate. Hosted invocation remains unavailable until its concrete
public transport and maintained caller adapter are selected and reviewed.

## Semantic checks and outcomes

The consumer must establish all of these conditions beyond schema syntax:

- Raw file digests and byte counts agree with the consumed records, and supplied
  statements equal their strict parses.
- Observation and decision timestamps parse as timezone-aware RFC 3339 instants.
  Schema format annotations alone do not enforce this; the consumer requires an
  available date-time checker or a separately implemented timestamp check.
- The owner's baseline and subject digests match the exact raw statements.
- Export digest sets match the consumed records with no duplicates; repeated
  inventory, selection, receipt, and mode identities agree with the inner records.
- Acceptance has the correct decision kind and original owner evidence.
  Withdrawals name their affected decision; supersessions also name their
  successor in the maintained source.
- A `current` assertion has an observed head and a separately received
  request-bound owner return. A field value alone cannot establish acceptance.
- Required member and client coverage is complete, with preserved bytes, modes,
  relevant state, and recovery evidence under the selected route.
- Public permission and publication/readback, when applicable, have their own
  separately consumed evidence.

Report one outcome: `matches-admitted-observation-at-capture`, `missing-evidence`,
`unavailable`, `withdrawn`, `superseded`, `dependency-changed`, or `contradiction`.
Structural, hash, statement, or subject contradictions take precedence.
Otherwise preserve a supplied withdrawal or supersession as its own outcome
rather than relabelling it missing data. Constructed cases report constructed
correspondence separately and never an actual-owner outcome.

## Private custody and public transfer

Retain private host paths, registrations, configuration and cache contents,
account details, credentials, and native logs in private custody. Digests require
their own transfer decision; they are not automatically public.

For a concrete public projection, Ivan selects the permitted fields and transfer
route. Bind the projection's exact bytes, field manifest, permitted commitments
to private originals, actual transfer decision, and publication/readback evidence.
The schema's `proposed-exact-packet` branch describes these inputs and supplies
no publication permission. With no selected packet or route, use `not-selected`.

This contract supplies neither a sanitizer nor an authenticated issuer. Digests
establish byte correspondence under the ordinary cooperative route.

## Source verification and completion

Run `python -m unittest tests.test_host_preservation_admission` for constructed
schema cases. These checks establish accepted and rejected record shapes,
including unavailable coverage and withdrawn observations. They establish no
semantic admission, real owner authority, live currentness, or runtime behavior.
Date-time format checking depends on the validator's optional format support;
the constructed tests cover timestamp field types, not complete timestamp syntax.

Maintained-source preparation is complete when this document, schema, and
constructed checks have clean review on the same revision and the validator
owner has consumed that revision. A production producer and semantic validator
require their own implementation and behavior evidence before actual admission.
Actual baseline acceptance, public transfer, host assessment, installation,
and release qualification remain with their existing owners and procedures.
