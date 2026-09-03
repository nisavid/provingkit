# Repository instructions

## Agent skills

### Issue tracker

Issues, PRDs, and Wayfinder maps are tracked in GitHub Issues for
`nisavid/provingkit`. See `docs/agents/issue-tracker.md`.

### Triage labels

Use the canonical `needs-triage`, `needs-info`, `ready-for-agent`,
`ready-for-human`, and `wontfix` labels. See
`docs/agents/triage-labels.md`.

### Domain docs

This is a single-context repository with root `CONTEXT.md` and system-wide
ADRs under `docs/adr/`. See `docs/agents/domain.md`.

## Project context

Read `CONTEXT.md` before planning or editing, and use its canonical language
in code, tests, documentation, issues, and commits. Where the glossary gives an
Agent Plugins term and a Claude equivalent, the Agent Plugins term is the
repository's word. Keep `README.md` as the verified human entrypoint and keep
detailed contracts, research, and specs under `docs/`.

Each plugin under `plugins/` is a package whose README names its validator
(`scripts/validate_<plugin>.py`), tests, evals, and content lock. The validator
owns the plugin's projections and content lock: edit source files and
regenerate with `--write-content-lock` rather than editing projections or
locks by hand.

## Git and validation

This is a personal `nisavid` project. Use `Ivan D Vasin <ivan@nisavid.io>` for
Git work and the `nisavid` GitHub account for repository mutations. Prefix
branches with `ivan/`. Use Conventional Commits for commits and pull request
titles; Cocogitto enforces them through the `commit-msg` and `pre-push` hooks
that `cog install-hook --all` installs.

Keep the primary checkout on `main` and do branch work in a persistent
sibling worktree under `<checkout>.wt/`. For every Git-backed task, use
`checkpointing-and-publishing-git-work` at the start, at clean checkpoints,
and before stopping. Every change requires `git diff --check`.

Before publication, run the validation that owns the touched surface:
`python scripts/validate_<plugin>.py .` and the plugin's tests through
`python -m unittest` for a plugin change, and
`python scripts/validate_source_skill_disposition.py .` whenever `plugins/`,
`release/`, or the disposition ledger changes. The workflows under
`.github/workflows/` run the same validators on every pull request.

## Operating Policy

- This repository uses agentic engineering and operations. Agents should perform assigned tasks autonomously until they reach a boundary that requires stakeholder policy or an unavailable control surface.
- The user reserves authority over project initiatives and over initiation or continuation of work sessions. Within an active user-directed session, agents should drive execution, review loops, commits, publication steps, and cleanup unless escalation is required.
- Escalate when a decision or action impacts stakeholder concerns and the stakeholder's policy is unknown or uncertain.
- Escalate when an action must be taken but the agent lacks an autonomous control surface for it.
- When escalating a decision and a set of plausible, distinct choices is known, use a multiple-choice input tool if one is available in the interactive context. Include a way for the human operator to provide custom input.
- When escalating an action with a known prescribed path, present the steps clearly for the human operator to perform. Prefer fewer steps; present commands in easily copyable blocks, and prefer a single one-line command when practical.
- For every escalation, make the return contract clear: state exactly what result, confirmation, artifact, or output is needed to hand control back to the agent, and make it easy to validate.
- Prefer verified repository facts over guesses or aspirational guidance.
- When adding new agent-facing instructions, ask whether the information is durable, non-obvious, and useful before scouting a task.
- Remove guidance that becomes redundant with ordinary file discovery.
