# Shared inputs and observation sketches

These sketches identify what each proposal would observe and what preparation can be reused. They are candidates for scope selection, not runnable contracts. Sources are the independent [completion](completion-evidence.md), [continuity](resumption-continuity.md), and [discovery](capability-discovery.md) reports, reconciled in the [design join](design-join.md).

## Reusable facts and their producers

| Fact and consumers | Existing source or proposed producer | Availability gap and refresh trigger | Work to attribute |
| --- | --- | --- | --- |
| Current intent: all three | Operator requests and amendments; agent retrieval and interpretation of applicable requirements | Source traces extract only selected prompts. Complete decision-time intent is unqualified. Refresh on amendment or newly applicable instruction. | Retrieval, selection, interpretation, and recurring context; no free structured contract. |
| Candidate identity: completion and continuity | Task-owned Git or artifact identity, selected by the agent and recorded by ordinary tools | The next proposal needs to establish ownership and coverage. Refresh after affected changes. | Selection and identity collection, plus revalidation. |
| Verification evidence: completion and continuity; discovery when locating verification | Actual tool outputs and check identities, with any claim/evidence pairing composed by the agent | Historical projections are incomplete. Pairing and semantic relevance are not mechanically established. Refresh after affected code, requirement, or check changes. | Execution, retention, pairing, retrieval, and consumer checking. |
| Completion, pause, or handoff meaning: completion and continuity | Current user direction and the agent's boundary statement | Existing Stop source does not extract structured boundary meaning. An exit code cannot supply it. Refresh with each new boundary or superseding request. | Interpretation and communication; avoid turning every pause into a completion review. |
| Accessible evidence: all three where relevant | Existing retained artifacts and native records; any proposed bounded lookup | Surviving hashes did not preserve missing originals. No complete handoff retrieval route is demonstrated here. Recheck after relocation, retention changes, or resumption. | Storage, lookup, access failures, and recovery. |
| Capabilities and readiness: discovery; other consumers at point of use | Source-defined help and command descriptions; operation-specific observations for readiness | Source existence and key presence do not establish a usable installed route. Refresh when the relevant version, environment, or operation changes. | Help lookup, any permitted readiness observation, failures, and stale-information handling. |
| Consumer effort: all three | Actual searches, rereads, repeated checks, questions, and task outcomes in a later accepted observation | The supplied reports do not measure operator savings or removable review work. Preserve the relevant sequence per observation. | Consumer effort separately from preparation, model usage, latency, and money. |

This table proposes no new record format or ledger. A producer can be reused only where its scope and identities match. Shared work counts once for combined use; standalone and marginal costs remain visible.

## Completion sketch

Observe an ordinary repository change through completion and the operator's verification. Retain current requests, affected candidate and check identities, the actual report, and the operator's checking actions. Compare ordinary reporting with a deterministic source-linked evidence view and omission of extra assistance. The missing measurement is whether the view reduces reconstruction while preserving trustworthy decisions and task quality. Easy, already-clear reports are legitimate controls; stale checks, superseded failures, amended requirements, and explicit pauses expose adverse cases. Semantic claim support remains a possible later Jev question, with its pairing producer charged separately.

## Continuity sketch

Use a genuine pause and resumption, possibly from different work than the completion sketch. Retain the accessible handoff, current unfinished request, candidate identity, evidence references, and what the resuming consumer reconstructs. Compare ordinary resumption with a minimal retained-reference view and omission. The missing measurements are retrieval success and actual resumption effort; repeated work must be observed rather than inferred from a long handoff. Include an already-clear resumption, a changed requirement, superseded verification, and inaccessible references. A semantic coverage check is a separate hypothesis, not necessary to investigate operator benefit.

## Discovery sketch

Observe a naturally occurring first code-location or capability-choice decision in an unfamiliar repository task. Retain the request, visible instructions/help, discovery actions, chosen path, and result. Compare ordinary search, a compact relevant reference, on-demand detail, and omission of added information. The missing observation is which work actually occurs and whether information improves the choice or removes effort. Explicit commands, irrelevant references, stale information, and unavailable routes are useful contrasts. No Jev arm is currently justified by a demonstrated residual ambiguity.

## Contract preparation

A natural task may supply both discovery and completion boundaries. Share that evidence without making continuity wait for such a task or forcing all three into one workload. Reconcile learning effects and overlapping savings before choosing comparisons. Under the existing acceptance process, the next concrete contracts must state supported inputs, interventions, contrasts, measurement, limits, and the decision their results can support. The sketches do not authorize execution, assume all three need trials, or require another historical audit.
