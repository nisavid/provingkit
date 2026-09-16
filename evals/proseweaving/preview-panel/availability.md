# Model and harness identities

The [recovered operator requirement](https://github.com/nisavid/provingkit/issues/75#issuecomment-5690487627) selects Claude Opus 5, Claude Fable 5.1, GPT 5.6 Sol, and GPT 6 Astra. Sol remains a comparison subject; its retired worker/reviewer preference does not remove it from this roster. The requirement permits reproducible choices of harness and effort. [panel.json](panel.json) fixes the ordered selections below before any output is generated.

Metadata-only observations on 2026-09-16 UTC:

| Subject | Selected native surface and exact selector | Settings | Observed availability |
| --- | --- | --- | --- |
| Claude Opus 5 | Cursor Agent 2026.09.10-fd3934a, `claude-opus-5-thinking-high` | Thinking, high, fast disabled | Listed by `agent models`; `agent status --format json` reports authenticated. |
| Claude Fable 5.1 | Cursor Agent 2026.09.10-fd3934a, `claude-fable-5-1-thinking-high` | Thinking, high, fast disabled | Listed by `agent models`; same authenticated surface. The listing marks this model NO ZDR; this protocol supplies only public repository fixtures and candidate instructions. |
| GPT 5.6 Sol | Codex CLI 0.154.0, `gpt-5.6-sol` | High, normal service; all other controls frozen in run manifest | Listed by `codex debug models`; high is supported. `codex login status` reports ChatGPT login. |
| GPT 6 Astra | Codex CLI 0.154.0, `gpt-6-astra` | High, normal service; all other controls frozen in run manifest | Listed by `codex debug models`; high is supported. Same authenticated surface. |

These routes keep each enabled/disabled pair inside one model and harness. They do not establish a cross-harness model ranking. All requested subjects are advertised; no substitution has been made. Selector exposure and authentication do not establish quota, isolation, native routing observability, returned immutable model identity, or successful execution. No comparison or model execution probe was run during preparation.

Claude Code 2.1.270's local `claude auth status --json` reported `loggedIn: false`, `authMethod: none`. This did not establish an authenticated Claude Code route; selecting the available Cursor route avoids making a claim about it. No credential acquisition, alternate account inspection, or global configuration change was performed. Cursor's observed listing did not expose Astra, which remains on Codex.

Recheck the selected identities at issue 71 kickoff and before freezing the run manifest. Record selector exposure, authentication, remaining capacity when observable, and actual execution identity separately. The launch recipe must establish isolated configuration and native selection evidence where supported; those capabilities remain for issue 71 to verify against the qualified preview. If a selected route is unavailable, report the missing capability to the orchestrator before replacing a model or harness. A dated preparation observation is not future runnability.
