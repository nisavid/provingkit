# Developing Praxis

This page is for people who contribute to Praxis, fork it, or work with its
internals. It stays in the source repository and is not part of an installed
copy. The [README](README.md) is the page for people using the plugin.

## Layout

    plugins/praxis/
    ├── plugin.json                      # Canonical Agent Plugins v1 manifest
    ├── .claude-plugin/plugin.json       # Claude adapter manifest
    ├── skills/
    │   └── constructing-agent-policies/
    │       ├── SKILL.md
    │       ├── references/              # policy-design.md and evaluation.md
    │       ├── scripts/                 # policy_eval_runner.py and gh_stub.py
    │       ├── agents/openai.yaml       # Codex skill adapter
    │       └── evals/trigger-evals.json # Trigger corpus
    ├── topology.json                    # One-skill roster and its ownership
    ├── README.md                        # Front page for people using the plugin
    ├── DEVELOPING.md                    # This page
    ├── CHANGELOG.md
    └── LICENSE

The canonical manifest is `plugin.json`; the Claude manifest projects its
identity. `topology.json` records the roster and the operations each skill
owns, and `scripts/validate_praxis.py` holds the same roster. Each new skill
needs its own invocation and owner boundary. Runtime resources live in the
skill tree so each target projection can carry them: the two references, the
two Python scripts, and the Codex adapter. The runner and its `gh` stub ship
because the installed skill reads them after the build, to run its
evaluations.

The release projection copies only an allowlisted subset of this tree into
each target's installable plugin tree. Every target leaves out
`topology.json`, this page, and the skill's `evals/` directory; the Codex
adapter ships only in the Agent Plugins target. The
[release artifact projection](https://github.com/nisavid/provingkit/blob/main/docs/release-artifact-projection.md)
document describes the policy and the builder.

## Repository release validation

The [README](README.md#package-validation) lists the package check, which also
runs in an installed copy.

Repository release validation additionally runs, from the repository root:

    python -m unittest tests.test_validate_praxis tests.test_policy_eval_runner
    python scripts/validate_praxis.py .

The validator checks the manifests, topology, exact skill roster, root file
inventory, required resources, trigger corpus shape, public test sources,
portability, and the content lock. `tests/test_validate_praxis.py` exercises
this source contract with isolated fixtures; `tests/test_policy_eval_runner.py`
exercises the runner with fake harnesses and a recording GitHub stub. These
checks make no live provider or host claim.

`release/plugin-content-locks/praxis.json` pins the plugin tree, both public
test modules, and the declared evaluation corpus. The validator is its only
writer:

    python scripts/validate_praxis.py --write-content-lock .

`release/provingkit/definition-v1.json` records the lock file's SHA-256 as the
Praxis content identity, and the validator does not write it. After a relock,
set that `sha256` to `sha256:` plus the new lock file's digest, then run
`python scripts/validate_provingkit.py .`, which checks it.

## Evaluation evidence

The constructor's transfer cases are authored under
`evals/praxis/constructing-agent-policies/` and declared in the validator.
Their [README](https://github.com/nisavid/provingkit/blob/main/evals/praxis/constructing-agent-policies/README.md)
describes the cases, the answer-sheet operator, the acceptance bar, and the
permission conditions, and shows how to validate every case without running
a model. The skill's trigger corpus is
[trigger-evals.json](skills/constructing-agent-policies/evals/trigger-evals.json):
exact `{query, should_trigger}` items with unique queries and both outcomes.
The content lock and the Kit definition digest include both. Source
membership grants no release, installation, or live qualification authority.
