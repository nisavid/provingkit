# Changelog

## Unreleased

- Establish Praxis as the plugin for work stewardship, with independent
  workflows and optional integrations.
- Define Aeon Bell as the first equipment for shared gate observation, task
  registration, and conditional dispatch.
- Add the canonical Agent Plugins manifest, Claude projection, and initial
  skill topology.
- Add the engine-directed Aeon Bell tick: `tick start`, `tick submit`, and
  `tick status` issue one bound action at a time (`task_read`, `observe`,
  `send`, `emit`, `heartbeat_set`) and take its typed result or the
  failure form; the engine runs the plan and result cycles, reservation,
  recheck, report, notice, acknowledgement, the scheduling decision, and
  the artifact lifecycle itself. `codex_status.py observe` gains
  `--report`. The schedule's registry gains `tick_in_progress` and
  `tick_readable`. The monitor recipe is replaced by the directed one;
  legacy monitor commands stay valid.
