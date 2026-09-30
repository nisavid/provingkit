# Praxis

Praxis is Provingkit's plugin for work stewardship: shaping, conducting,
recovering, and completing agentic efforts. Its first published skill,
`constructing-agent-policies` (`skills/constructing-agent-policies/SKILL.md`),
turns operator intent and incident evidence into a situational decision rule,
places it with the component whose work it governs, and evaluates it on the
target models.

## Work stewardship

An effort brings together intent, a graph of work, participants, context,
artifacts, and obligations. Praxis provides methods for keeping those parts
coherent as work proceeds. Later workflows may cover lifecycle orchestration,
triage, handoff, closeout, and recovery.

Praxis works independently. Wayfinder, To Tickets, and their replacements can
supply optional integrations, but do not own its methods.

## Public skill

| Skill | Owns | Calls |
| --- | --- | --- |
| constructing-agent-policies | Agent policy construction and evaluation | None |

An agent policy is a situational rule for when an agent acts, waits, asks, or
stops. Use the skill to create, correct, test, or re-evaluate one. The
[skill](skills/constructing-agent-policies/SKILL.md) states its principles and
steps; the
[policy design](skills/constructing-agent-policies/references/policy-design.md)
and [evaluation](skills/constructing-agent-policies/references/evaluation.md)
references carry the detailed method. Codex addresses it as
`$praxis:constructing-agent-policies`.

The installed skill includes its evaluation runner,
`skills/constructing-agent-policies/scripts/policy_eval_runner.py`, and the
recording `gh` stub beside it. The runner executes frozen policy evaluation
cases against Claude Code or Codex with GitHub effects stubbed, grades each
run, and scores the results against the acceptance bar. Its presence is not a
model evaluation result.

## Composition

Praxis carries an effort's context, obligations, and results through the
specialist that owns each operation:

- Rolecasting owns worker topology and model selection.
- Tricritical owns review, adjudication, and revision.
- Versionkeeping owns Git checkpoints and publication.
- Mergecraft owns the pull-request lifecycle.
- Artifact Customs owns third-party component lifecycle.
- Proseweaving owns human-facing prose.

Each task keeps its own operation authority. Praxis does not duplicate a
specialist's procedure.

## Package validation

From the package root:

    python3 skills/constructing-agent-policies/scripts/policy_eval_runner.py --help

## Developing this plugin

This section is for people who want to contribute to Praxis, fork it, or work
with its internals. An installed copy leaves out the topology
(`topology.json`), the evaluation corpora, the validator, and the tests; they
stay in the source repository. The
[developer page](https://github.com/nisavid/provingkit/blob/main/plugins/praxis/DEVELOPING.md)
describes the source layout, repository release validation, and the
evaluation evidence.
