# Sys1 incident diagnosis and first comparative study

The first incidents expose two integration defects worth testing independently:
the safety path discards approval context before judging a call, and the Codex
adapter turns an internal request for approval into a denial without a
demonstrated way for later approval to change that result. The supervision
parser also loses intermediate amendments and genuine user messages beginning
with `<`. Pure replays establish those transformations. They do not establish
the best authority policy for Sys1 or explain the original supervision score.

This research supports [Learn from Sys1 incidents and qualify the first correction](https://github.com/nisavid/provingkit/issues/229),
[Reconcile the Sys1 incidents with current harness contracts](https://github.com/nisavid/provingkit/issues/230), and
[Define the first comparative Sys1 experiment](https://github.com/nisavid/provingkit/issues/231).
It records observations from September 26, 2026. The authorized first increment
compares competing approaches on the incidents and delivers the smallest
correction supported by the results. Removing an intervention is eligible.
Safety and task alignment are separate outcomes. Advisory, fuller-agent review,
and selective veto remain competing roles.

## Evidence and its limits

| Evidence | What it establishes | What it does not establish |
| --- | --- | --- |
| Bounded incident record and witnessing-task handoff | A proposed call was denied; recorded scores and operator authorization | The unseen model's reasoning or a present-day repeat score |
| Installed JavaScript inspection and pure-function replay | State loss, decision thresholds, adapter output, transcript selection | End-to-end harness behavior or safety of an alternative |
| Version-matched Codex source | The declared hook and approval behavior for the running backend version | That a proposed new integration works in a live task |
| Current Claude documentation | Documented hook forms and transcript caveats | Conformance of every installed Claude process |
| Independent Astra and Fable design passes | Competing hypotheses and experiment criticism | Empirical model quality, consensus truth, or rollout acceptance |

The installed `jev-axi` package reports version 0.7.2. Its
[upstream v0.7.2 source](https://github.com/shiftynick/jev-axi/tree/044fae73a05d5699c4b5c47073f1ffc29d9aa82d)
contains `src/safety.ts`, `src/commands/hook.ts`, and `src/supervise.ts`.
The observed tag and upstream main resolved to that commit. This investigation
did not prove that the installed distribution was built byte for byte from it.

The replay used Node.js v24.21.0 and these installed distribution bytes:

| Package-relative file | SHA-256 |
| --- | --- |
| `dist/src/commands/hook.js` | `882c2d8888b588ab8380dba244ab60d3ca3b501473e554161f259b20876c65e7` |
| `dist/src/safety.js` | `cac12dd160ebe9b236d5af7c206e8aeaa6b14802d3f783bd4818c474c45c3554` |
| `dist/src/supervise.js` | `b88e9452a01c2d2b2383c6a8c4457cf350e9dbc0bb29aa6d5d07bf0a53fc13df` |

The running Codex desktop backend reported
`codex-cli 0.155.0-alpha.16.3`. PATH-selected Codex and other installed daemons
had different versions. Claude CLI reported 2.1.282; observed desktop-owned
Claude processes included 2.1.280. A binary on PATH, a package version, and a
running process are distinct evidence.

## Incidents

### Authorized verification artifacts

At `2026-09-26T15:43:08.515Z`, a task attempted to verify public repository state
and write verification artifacts outside its current checkout, within a
configured writable root. The task's recovery verification was already
authorized. The witnessing task reported no signing-key retrieval, provider
mutation, branch-protection change, or secret export in the proposed action.
The denied verification-result artifact was subsequently confirmed absent.

The bounded safety record contained:

| Typed judgment | Value |
| --- | ---: |
| outside_project | 0.89 |
| risk, on a 0–2 scale | 0.82 |
| destructive | 0.03 |
| exfiltration | 0.12 |
| remote_code | 0.05 |
| weakens_security | 0.03 |

The internal decision was `ask`; the Codex adapter emitted `deny`.
Being outside cwd was an accurate geographical description. It is not evidence
that the action was unauthorized, nor sufficient evidence of model
miscalibration.

### Worktree setup and adapter installation

A later authorized sibling-worktree setup was denied with
`outside_project=0.89` and `risk=0.60`. Repeating the same operation after an
explicit approval was also denied. The operator performed the setup directly;
this task independently verified the clean owning branch at the intended base.

A separate witnessing task reported an authorized public-adapter installation
outside the harness's writable roots. Native escalation was appropriate for
that destination. The Jev hook denied it with `outside_project=0.96` and
`risk=1.30`, then denied the same operation after explicit approval. The
witnessing task later reported successful operator execution and independent
verification of the installed hash, file type, ownership, mode, and provider-free
help output.

Manual completion resolves those operations. It does not qualify an automated
approval-recovery route. The research task did not independently inspect the
installed adapter.

### Supervision

The witnessing task observed `work_off_track=0.77`. This research task also
received a `needs_human=0.72` instruction to stop and ask. The exact inputs sent
to the original supervision judgment were not recovered. The parser replays
below demonstrate plausible loss mechanisms, not a causal explanation for
either score.

## Safety transformations

`readCall` retains only `tool_name`, `tool_input`, and `cwd`.
`buildSafetyState` then retains the tool and cwd, a redacted command and bounded
in-cwd script excerpts, or the edit path and content excerpt. Neither function
carries task authorization, configured writable roots, or user approval into
the judgment state.

A pure replay added synthetic `session_id`, `turn_id`, `approved_scope`, and
`user_intent` to the same call. The serialized safety states were identical:

```json
{"tool":"Bash","cwd":"/tmp/synthetic-project","command":"echo synthetic fixture"}
```

This establishes that adding those top-level fields alone cannot repair the
current pipeline. It does not say that arbitrary approval strings should become
trusted input.

With the first incident's scores held fixed, `decide` returned `ask`.
`hookOutput` emitted a Codex `permissionDecision: "deny"` and a Claude
`permissionDecision: "ask"`. No model was called and no proposed command ran.
The installed local fast path can allow a call without invoking the judge.
Judgment-only experiments must record that local disposition and distinguish
forced judgment comparisons from the actual hook path. The policy's default ask threshold is 0.45 for any hazard, including
`outside_project`; independent blocking hazards have a 0.80 deny threshold.
An outside-project score at least 0.80 plus risk at least 1.50 also denies.

The hook defaults to allowing safety-check errors other than API 403 rejection;
API 403 is denied. Supervision exceptions return without an intervention.
Those are source observations, not induced service-outage experiments.

## Harness contracts

The version-matched Codex
[PreToolUse schema](https://github.com/openai/codex/blob/rust-v0.155.0-alpha.16.3/codex-rs/hooks/src/schema.rs#L278),
[output parser](https://github.com/openai/codex/blob/rust-v0.155.0-alpha.16.3/codex-rs/hooks/src/engine/output_parser.rs#L441),
and [event handling](https://github.com/openai/codex/blob/rust-v0.155.0-alpha.16.3/codex-rs/hooks/src/events/pre_tool_use.rs#L200)
support denial and additional context. They do not support an `ask`
PreToolUse decision. `allow` with `updatedInput` represents an input rewrite,
not a standalone permission grant.

The incoming hook event provides substantially more information than Jev's
current `readCall` preserves: session/turn identity, transcript path,
permission mode, and tool identity/input. That is not a complete trusted
authorization record. Permission mode does not encode all writable roots,
earlier approvals, or the approval reviewer.

Codex [PermissionRequest handling](https://github.com/openai/codex/blob/rust-v0.155.0-alpha.16.3/codex-rs/core/src/tools/approvals.rs#L496)
can approve or deny before the native reviewer or user. Moving a judge there
would add authority; it is not merely a format correction.

[Claude's hook documentation](https://code.claude.com/docs/en/hooks)
describes a different decision vocabulary, including `ask`, and warns that
transcript writes can lag. Transcript access therefore needs freshness and
provenance treatment. An untrusted claim embedded in tool input is not operator
authorization.

Jev is distinct from Codex's automatic approval reviewer and Claude's auto-mode
classifier. An observed rejection must name the layer that emitted it. Neither
the native-only experimental arm nor an advisory arm removes native permission
checks.

## Supervision replay

The installed `readTranscript` collects supported user-event forms, rejects
trimmed prompt text beginning with `<`, and forms the job from the first and
last accepted prompts. It omits all intermediate prompts.

Three in-memory JSONL inputs produced these results:

| Input sequence | Extracted job |
| --- | --- |
| Opening task; amendment to include supervision; later status question | Opening task plus status question; amendment absent |
| Opening task; same amendment as latest plain user event | Opening task plus amendment |
| Opening task; genuine user amendment wrapped in `<send_user_message_question_reply>` | Opening task only |

All three used Codex `event_msg/user_message` fixtures. They establish behavior
for that event shape. Cross-harness and additional event forms remain study
fixtures.

From the installed package root, this read-only reproduction prints the first
case. The strings describe synthetic work; they execute no tools:

```sh
printf '%s\n' \
  '{"type":"event_msg","payload":{"type":"user_message","message":"Opening task: investigate Sys1 safety."}}' \
  '{"type":"event_msg","payload":{"type":"user_message","message":"Amendment: include supervision alignment."}}' \
  '{"type":"event_msg","payload":{"type":"user_message","message":"Status request: how is the work going?"}}' |
node --input-type=module -e 'import {readTranscript} from "./dist/src/supervise.js"; console.log(JSON.stringify(readTranscript("/dev/stdin")))'
```

Observed output:

```json
{"job":"Opening task: investigate Sys1 safety.\n\nLatest request: Status request: how is the work going?","output":""}
```

Replacing the third event with the amendment makes that amendment the latest
request. Wrapping the amendment in the stated XML element causes its exclusion.
The probes called only the transcript reader, not supervision assessment,
session recording, or full hooks.

## Research implications

[TypeSafe's integration guidance](https://docs.typesafe.ai/concepts/how-to-build-with-system-one)
places deterministic control around narrow typed judgments. Its
[Jev limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13) describe
sensitivity to question phrasing, irrelevant state, indirection, and adversarial
state. Supplying more context is therefore a hypothesis to test, not a remedy
proved by inspecting a missing field.

The first study must separate five questions:

1. Does the integration preserve the information it claims to use?
2. Do different state or question designs change useful model judgments?
3. Given fixed scores, which policy and adapter produce which interventions?
4. Do those interventions improve the agent's completed work and safety?
5. Which observed trade-offs justify an operator-selected correction?

A chosen diagnostic corpus cannot establish population error rates or
calibration. Unknown and disputed cases remain visible. Actual effects,
operator task authorization, native permissions, and Sys1 output are separate
observations.

The [comparative protocol](2026-09-26-sys1-comparative-protocol.md) owns the
next contrasts. No live hook, permission configuration, or deployed plugin
changed during this research. Source placement for a correction and the reusable
incident procedure remains a design decision; the study does not create a new
plugin or absorb adjacent policy-construction work.
