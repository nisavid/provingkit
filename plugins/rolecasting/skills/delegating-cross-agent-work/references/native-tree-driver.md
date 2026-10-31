# Ordinary Cloud native-tree driver

Use `scripts/native_tree.py` for the explicitly selected
`chatgpt-codex-native-tree-v1` profile. It plans supported native calls and keeps
local SQLite records. The current agent performs the calls through its native
tools. The script neither launches agents nor authenticates caller-supplied
evidence. Keep the strict [native profiles](native-codex-subagents.md) for
consumers requiring their version and identity contracts.

This route covers one current controller and its native child tree. Logical
roles can correspond directly while remaining native children. It supplies no
account-wide directory, independent chat, root wake, or cross-root restoration.
Cloud role duties and standing correspondence permissions belong to the
consumer's separately loaded policy; a directory entry grants no authority.

## Initialize once per controller

Recover the actual user grant, conditions and holds. Select topology and model
through the owning skills. Freeze task inputs, scope, verification and stop
conditions before preparing any operation. A generic coordinating-role plan
does not widen the separate read-only critic invocation plan.

Keep one task-owned store and a context JSON file containing exactly `run` and
`actor`. A run has these fields:

| Field | Meaning |
| --- | --- |
| `schema` | `native-tree-run-v1` |
| `run_id`, `controller_ref` | Local bookkeeping labels tied to this retained controller context; not native session or account IDs |
| `profile_id` | `chatgpt-codex-native-tree-v1` |
| `profile_sha256` | Digest of the selected driver/profile implementation |
| `capability_ref`, `capability_sha256` | Retained current native-schema observation and its digest |
| `product_version` | `{state: "observed", value, evidence_ref}` or explicit `{state: "unavailable", reason}` |

The actor is `{role, generation}`. Bootstrap its root binding with
`--create` and `bind-role`. A binding has `schema: native-tree-binding-v1`,
`run_id`, `controller_ref`, `role`, positive integer `generation`, `relation`,
`native_target`, `observation_ref`, `source_kind`, and `selection_ref`.
Root evidence uses `harness-context`; child evidence uses
`native-tool-result` or `native-inventory`. Only an unaddressable root may have
a null target. Optional `agent_id`, `session_id`, `task_id`,
`native_parent_target`, and `logical_owner` remain separate and absent when
unexposed. Never manufacture them from a role name or target string.

A created child binding must cite the recorded result of its exact claimed
spawn, including the current native `{task_name: ...}` return. Adoption from
inventory is supplied-controller bookkeeping, not proof of an unobserved
creation. Rebinding is explicit and preserves earlier generations and claims.
For a spawn binding, `observation_ref` is the observation envelope's
`evidence_ref`; `selection_ref` exactly matches the spawn plan's value.

Withdraw a directory binding with
`retire_role(role, generation, evidence_ref)`, or the CLI request
`{"operation":"retire-role","role":"worker","generation":1,"evidence_ref":"retained-decision"}`.
The example names are placeholders. Retirement records the exact generation
and supplied decision reference without changing its identity. Repeating the
same retirement is an idempotent lookup; a different reference conflicts.
Inspection exposes `retired: true` and retains the retirement record. New
preparation and claims through that binding are refused, including work
prepared before retirement. An exact existing-command lookup remains readable
and cannot emit a new call.

Retirement is a local directory decision, not a native stop, evidence of
nondelivery, or revocation of the underlying authority. Pending obligations and
native activity hazards remain. The unchanged owner can still reconcile its
obligations. A deliberate new generation may replace the binding; using the
same native target preserves its existing activity hazard. A different observed
target can receive new work while the old identity and uncertainty remain in
history.

Opening a store requires its exact frozen run; it never silently creates a
replacement. A new controller requires a new run and explicit handoff, even if
an old target string or database remains readable. Mutable stores, context,
payloads and obligations never belong in a published environment image.

## Prepare, claim, act, observe

The CLI takes `--store` and `--context`; one JSON request arrives on standard
input. It emits one JSON result. Duplicate keys, nonfinite values and unknown
request fields fail. Python callers use `NativeTree` with the same contracts.

For an operation, send `operation: prepare-claim` plus `plan`, `action`, `role`,
`generation`, `payload`, and `mode`. The plan has `schema: native-tree-plan-v1`,
`run_id`, unique `command_id`, external frozen `plan_sha256`, `request_sha256`,
`authority_ref`, `verification_contract_ref`, and `stop_ref`. Assigned work
also binds `assignment_id`, immutable `owner` and `reply_to` role/generation
references; creation requires `selection_ref`.

Informational and other non-work operations may omit assignment correlation.
If they supply `assignment_id`, `owner`, and `reply_to`, that group must name an
already established assignment with the same owner and reply recipient. It
does not create an assignment or transfer its ownership. Old stored commands
whose correlation lacks an established assignment remain readable in
inspection, with that correlation marked unestablished and no assignment
reconciliation suggested. They do not manufacture an activity record or gain
another emission.

`request_sha256` hashes canonical JSON of the complete native payload.
`input_sha256`, when supplied, separately identifies immutable business inputs
and can safely appear inside the message. Without it, the first request digest
becomes the assignment's input identity. Do not try to embed a payload's own
hash inside that payload. Canonical JSON uses sorted string keys, compact
separators, UTF-8 and no nonfinite numbers. Message strings retain their exact
newlines and Unicode. A changed command under an existing ID is an error.

Only `claimed: true` returns `native_call`. Invoke that exact native operation
once. The transaction records uncertainty before returning it; losing the
output consumes the claim. Repeated lookup returns no call. Native arguments
receive no invented session, idempotency or correlation fields; application
correlation and reply intent belong in the message.

| Action and mode | Native operation |
| --- | --- |
| `spawn`: `fresh` / `inherit` | `collaboration.spawn_agent` |
| `notify`: `information` / `reply` | `collaboration.send_message` |
| `activate-or-steer`: `assign` / `continue` / `steer` | `collaboration.followup_task` |
| `interrupt`: `request` | `collaboration.interrupt_agent` |
| `inspect`: `inventory` | `collaboration.list_agents` |
| `wait`: `bounded` | `collaboration.wait_agent` |

Fresh creation requires `fork_turns: none` and explicit supported model/effort.
Inherited creation requires `fork_turns: all` without overrides. Inventory and
wait have null role/generation. Root follow-up is unsupported. Inspect current
native schemas before use; model eligibility and capability remain the
selection owner's responsibility.

Record the actual response with `operation: observe-inspect`, `command_id`,
`source_kind` and `raw_observation: {observation_id, raw, evidence_ref}`.
Sources are `native-tool-result`, `native-inventory`, `harness-final-event`,
`worker-report`, and `owner-verification`. Observation identity binds the full
source and collection context, not only raw bytes. Replay cannot relabel it.
Unknown shapes remain retained without derived facts.

For inventory used to permit continuation or clear an activity hazard, first
claim and execute a fresh inventory command. Record its response against the
subject work command with `collected_by` naming that inventory command. The
collector must follow the relevant work or closure. Late recording of an old
snapshot cannot create freshness. Local `inspect()` reads stored state; it
does not perform this native query.

## Result evidence and acceptance

One unresolved assignment reserves the actual child target. Keep native
parent, assignment owner and reply recipient distinct. A sibling-owned task
needs an explicit correlated application reply to its owner; a parent final
does not reroute itself.

A worker result contains `assignment_id`, recipient `generation`,
`input_digest`, `result`, and its canonical `result_digest`. Owner verification
contains the same identities, `usable` as a strict Boolean, and `evidence_ref`.
The current immutable owner calls `accept` with `assignment_id`, recipient
`generation`, `result_digest`, and that recorded `verification_ref`.
Missing, changed, stale or failed verification cannot accept work.
The verification's raw `evidence_ref`, its observation envelope's
`evidence_ref`, and acceptance's `verification_ref` must be identical.

Inspect the assignment's evidence projection before consuming it. Profile
maxima are ceilings; absent dimensions stay unavailable. Requested model and
authority never prove their execution or enforcement. Correlated worker output
is self-reported. Only the narrowly qualified harness final of a fresh child
with one unambiguous input can establish controller-observed output. Its exact
payload is content, including any embedded status or model claims. Reused or
ambiguous targets retain separate native status and business-result evidence.
Neither final emission nor a completed inventory establishes correctness or
acceptance. Enforce frozen consumer minima without lowering them.

Logical acceptance does not stop a native turn. Reusing its target requires
completed inventory collected after closure; aliases and new generations of
the same target cannot clear that hazard. A different observed target may
receive different work while the old history remains preserved.

Native activity belongs to claimed work attempts and their recorded targets,
independently of the current role directory. A late spawn receipt reserves its
actual target even when its old generation can no longer be bound. Explicit
retry attempts can expose different children; each child remains represented.
Conflicting target observations are retained rather than replacing one target
with another. Directory retirement and logical abandonment do not erase those
attempts.

Inspection exposes this derived `activities` list and each assignment's
`native_targets`. The singular `native_target` is only a compatibility summary
when exactly one target is known. Each target needs its own qualifying
completed inventory after closure and target discovery. A completed observation
for one retry child cannot release another. Once an earlier activity has such
completion evidence, unrelated later work does not make that old activity
unfinished again; later work has its own activity record.

## Recover deliberately

A running previous status proves no completed interruption. Wait timeout,
inventory absence and lost receipts prove no nondelivery. Use current
observations or an explicit owner disposition before further effects.

`reconcile` records `keep-unknown`, `use-observed-result`, `abandon`, or
`authorize-new-attempt`. Its evidence identifies a reconciliation, owner
decision and supporting evidence; retry additionally requires an explicit
supported basis. The owner must establish that basis under the real grant.
The helper checks relationships, not the truth of external evidence.

A replacement references that exact reconciliation via
`predecessor_reconciliation_ref`, preserves the frozen assignment/input/target,
and consumes its retry authorization once. Its transport payload must match
the exact reconciled predecessor, including when that predecessor is a
continuation with a different message from the assignment's first request.
The assignment's business-input identity stays unchanged. A new ID or a `continue` label
cannot bypass an uncertain attempt. Abandonment preserves outstanding native
activity. Readable records alone never transfer ownership or restore a lost
controller. Keep failures and partial results in the handoff.

Use inspection's `reconciliations` to recover retained decisions and their
`consumed_by` values. Null means no successor has consumed that record; a
command ID identifies the consuming successor without rewriting the original
decision. A filtered view includes relevant predecessor authorizations.
`next_actions` only advertises claim when the same eligibility checks used by
`claim()` currently pass. `blocked_actions` gives known refusal reasons; it
does not authorize bypassing a retired binding, occupied target, stale
generation or consumed retry decision. Inspection returns no native call.

A lost spawn receipt can leave its recipient legitimately unbound. Its current
immutable owner can preserve, abandon, or explicitly authorize an unchanged
retry without inventing a native target. Reconciliation does not supply that
missing identity. Addressed operations and result acceptance retain their own
binding checks; a retry remains one-use and preserves the original uncertainty.
