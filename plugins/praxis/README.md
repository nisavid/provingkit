# Praxis

Praxis is Provingkit's plugin for work stewardship: shaping, conducting,
recovering, and completing agentic efforts. Its first published skill,
`constructing-agent-policies` (`skills/constructing-agent-policies/SKILL.md`),
turns operator intent and incident evidence into
a situational decision rule and evaluates it on the target models.

## Work stewardship

An effort brings together intent, a graph of work, participants, context,
artifacts, and obligations. Praxis provides methods for keeping those parts
coherent as work proceeds. Later workflows may cover lifecycle orchestration,
triage, handoff, closeout, and recovery. Each new skill needs its own
invocation and owner boundary.

Praxis works independently. Wayfinder, To Tickets, and their replacements can
supply optional integrations, but do not own its methods.

## Public skill

| Skill | Owns | Calls |
| --- | --- | --- |
| constructing-agent-policies | Agent policy construction and evaluation | None |

The skill maps seed intent and incidents to facts, values, gates, actions,
stops, and re-entry triggers. It places the rule with the component whose work
it governs. The policy-design.md and evaluation.md references carry the
detailed method. Codex addresses it as $praxis:constructing-agent-policies.

The skill includes scripts/policy_eval_runner.py and scripts/gh_stub.py. The
runner is read after the build to run controlled Claude Code and Codex
evaluations with external tool effects stubbed. Its presence is not a model
evaluation result.

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

## Package shape

The canonical manifest is plugin.json. The Claude manifest projects its
identity, and topology.json records this one-skill roster and its ownership.
The installed skill carries SKILL.md, two references, two Python scripts, and
agents/openai.yaml. Runtime resources are in the skill tree so each target
projection can carry them.

## Validation

From the repository root:

    python -m unittest tests.test_validate_praxis tests.test_policy_eval_runner
    python scripts/validate_praxis.py .

The validator checks the manifests, topology, exact skill roster, required
resources, public test sources, portability, and the content lock.
tests/test_validate_praxis.py exercises this source contract with isolated
fixtures; tests/test_policy_eval_runner.py exercises the runner with fake
harnesses and a recording GitHub stub. These checks make no live provider or
host claim.

release/plugin-content-locks/praxis.json pins the plugin tree and both public
test modules. The validator is its only writer:

    python scripts/validate_praxis.py --write-content-lock .

The constructor's evaluation corpora are authored under
evals/praxis/constructing-agent-policies/. Their filenames and validation
contract must be declared in the validator when they land, then included in
the content lock and Kit definition digest. No corpus is required by this
one-skill shell. Source membership grants no release, installation, or live
qualification authority.
