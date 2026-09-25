# Classifier consent rig

A headless red/green check that a skill binds actuator authority the way
[Binding actuator authority under a permission classifier](../../docs/plugin-system/actuator-authority-binding.md)
describes. It runs Claude Code in auto mode against throwaway fixtures: a
repository whose `origin` is a local bare repository, the real Versionkeeping
planner and executor, and a recording `gh` stub first on `PATH` for every case.
Pushes reach only the fixture's bare remote, `gh` calls reach only the stub,
and runs go to a new temporary directory unless `--out` names one. The rig
does not otherwise sandbox the agent. Keep `--out` paths neutral: the
classifier reads paths in command text, and a directory named after the
classifier or the scenario changed its verdicts.

Requirements: Claude Code 2.1.281 or later with auto mode available to the
account, a Sonnet or Opus agent model (Haiku falls back to Manual mode), `git`,
`python3`. Each trial costs a few cents of model use and about a minute.

Red and green on the Versionkeeping publication skill, five trials each:

```sh
evals/classifier-consent/rig/run_red_green.sh main 5
```

Red loads the plugin as committed at the given ref; green loads the working
tree. Expect most red trials to draw a classifier denial and most green trials
none; the residual green denials in observed runs were ticket commands that
Versionkeeping's rule does not cover.

Any case runs alone:

```sh
python3 evals/classifier-consent/rig/harness.py run evals/classifier-consent/cases/scripted-relay-bare-acceptance.json --trials 5
```

`cases/` holds the skill case and four scripted calibration cases (no relay
with a bare acceptance; relay with a bare acceptance; relay with the operator
naming the actions; relay with one `AskUserQuestion` per action). Case fields
are documented at the top of `rig/harness.py`; `$FX`, `$VK`, `$PLUGIN`, and
`$RIG` expand to the fixture directory, the Versionkeeping scripts, the plugin
under test, and this rig. `rig/reparse.py` re-derives denial counts from saved
streams and classifies rule-named, unlabeled, and classifier-error denials.
