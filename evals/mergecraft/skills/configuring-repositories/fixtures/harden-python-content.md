# Hardening a Python tool and its instruction plugin

Please prepare extensive CI hardening for the public `sample-maintainer/prompt-linter` project. The concerns are accidental content/projection drift and security issues in its Python code. I want useful checks and a dependable merge gate, with GitHub Actions as CI. Keep the implementation reviewable before hosted qualification.

Project inputs:

```text
pyproject.toml                      Python >=3.12; package prompt_linter
src/prompt_linter/check.py          parses plugin manifests and paths
tests/test_check.py                 standard-library unittest tests
plugins/scribe/plugin.json          canonical manifest
plugins/scribe/.claude-plugin/plugin.json  generated adapter
plugins/scribe/skills/editing/SKILL.md
plugins/scribe/skills/editing/references/style.md
scripts/validate_scribe.py          validates manifest, resources, adapter equality
scripts/write_scribe_adapter.py     maintained projection writer
```

The documented commands are `python -m unittest discover -s tests` and `python scripts/validate_scribe.py .`. Neither command downloads dependencies. Adapter regeneration is `python scripts/write_scribe_adapter.py .`; validation is read-only. The repository's content is predominantly instruction Markdown and JSON, with the Python parser under `src/` and its tests.

Existing CI runs those tests on `push` to `main`, with `contents: write` at workflow level and no PR trigger. Its action dependencies use moving version tags. There is no CodeQL setup. The proposed future integration route is PRs to `main`; merge queue is a possibility, not an adopted choice. No actual hosted check producer or result identity has been recorded.

The public fixture may eventually use free standard GitHub-hosted Linux runners. No schedule, paid runner, subscription, deployment secret, artifact upload, or cache persistence is selected. This local exercise does not admit any hosted run. Prepare workflow/source proposals locally and fetch public documentation; activation, code coverage, and gate behavior have not been observed.
