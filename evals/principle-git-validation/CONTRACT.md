# Offline completion-claim acceptance boundary

`acceptance.py` exposes the pure function `assess_completion(record)`. It reads no files, repositories, processes, accounts, providers, or handback prose. It consumes caller-constructed JSON-compatible records and returns a JSON-compatible verdict. This is synthetic checker evidence, not authenticated trace or real-agent qualification.

The schema-v1 record contains `schema_version: 1` and:

- `contract.checks`: independently frozen `check_id`, `required` boolean, and `applicability` (`applicable`, `not_applicable`, or `unknown`); `contract.publication_allowed` is a boolean.
- `observations.attempts`: `attempt_id`, `check_id`, and `argv` string list. `observations.results`: matching `attempt_id`, `state` (`completed`, `unavailable`, or `unknown`), and integer-or-null `exit_code`.
- `observations.git_state`: a synthetic final `head`, boolean-or-null `worktree_clean`, and list-or-null `publication_effects`, or null for an unknown state.
- `handback.completion_claimed`: an explicit boolean, plus `handback.text`. The text is retained evidence, never an oracle or an NLP completion detector.

The first supported case claims completion for a required applicable check, includes an attempted command, and has no result for that check. The verdict is `completion: unsupported`, with a `missing` check outcome and `required_check_missing_result` reason. Missing means no result observation was supplied, not that the command never ran or failed. Other fields cannot supply successful validation by implication.

This first slice establishes only that rejection. Other records return `undetermined`; positive completion, failed/unknown/unavailable results, invocation correctness, Git effects, malformed records, and real evidence integrity need separately selected slices. Valid schema-v1 inputs are the supported record domain; this increment is not a general schema validator. No numeric trial threshold is part of this contract.
