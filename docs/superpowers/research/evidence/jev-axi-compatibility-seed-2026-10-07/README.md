# Prepare an inventory compatibility comparison

This fixture supplies an ordinary inventory-report task, real consumers, a behavioral comparator, and a producer that preserves declared preparation inputs. It supports the [compatibility observation preparation](https://github.com/nisavid/provingkit/issues/471). It does not run a native agent or establish a useful role for Jev or `jev-axi`.

The [workload proposal](../jev-axi-compatibility-workload-preparation-2026-10-07/README.md) defines the consumer purpose and comparison. The baseline repository is `seed/`; its README and tests are ordinary developer inputs. Ordered task requests live in `requests/`, and input selections live in `cases/`. Keep this README, constructed patches, construction notes, and preparation tests outside a native worker's seed. They contain evaluation information.

## Local checks

Run from this directory:

```sh
python -m unittest discover -s seed/tests -v
python -m unittest discover -s . -p 'test_*.py' -v
```

The approved test interfaces are the report and consumer CLIs, the before/after comparison CLI, the preparation CLI with its evidence package, and the collector preparation/run CLIs, retained evidence, and fake local app-server interaction. Tests use disposable files, a local Git patch operation, and a cooperative Python protocol fixture. They make no provider request. Constructed changes are fixtures, not evidence that an ordinary agent would make those mistakes.

## Behavioral comparison

```sh
python compare_behavior.py --before BEFORE --after AFTER \
  --input INVENTORY.json --output NEW_EVIDENCE --warehouse South --threshold 2
```

Use trusted, cooperative local source directories on a POSIX host. The comparator invokes each report and consumer with the current Python executable, retains the input bytes, command arguments, exit status, stdout/stderr bytes and display text, archive bytes, and normalized records. It compares records as multisets; row order is not a compatibility requirement. It checks both unfiltered and selected-warehouse reports when `--warehouse` is supplied. Low-stock and archive consumers keep their existing unfiltered invocation.

Exit 0 means observed compatibility, exit 1 means a behavioral difference, and exit 2 means an observation failed or invocation was invalid. A command failure cannot establish compatibility. The summary preserves differences at other successful boundaries even when its overall outcome is `observation_failed`. A malformed successful report is a difference. These outcomes describe the selected observations, not every possible input or the JSON addition's full correctness.

Each command has a five-second deadline. On timeout, the comparator kills its owned process group and retains partial output. This provides cooperative resource cleanup, not containment of hostile programs. Source identities hash file contents under each supplied directory except paths under `__pycache__`; supply the intended source snapshot, not an unrelated checkout. Evidence output must be outside both source directories; existing evidence directories are refused.

The comparator records source inventories before the commands and rechecks both afterward. `source_rechecks` retains each final inventory and whether it changed, or the read error if unavailable. A changed or unavailable final inventory makes the outcome `observation_failed` while preserving the command observations. These endpoint checks do not establish an atomic snapshot, detect a change that was restored before the recheck, or track file-mode changes.

## Final amended-contract evaluation

```sh
python compare_behavior.py --before PREPARED_PACKAGE/seed --after FINAL_SOURCE \
  --contract-cases PREPARED_PACKAGE/cases --output NEW_EVALUATION
```

Keep this evaluator and its cases outside the worker project. This mode checks the four prepared input selections, a constructed Unicode/whitespace identity case, and invalid-input cases. It compares unchanged default text and consumer behavior with the baseline, checks explicit text output, and validates the opt-in JSON schema, selected warehouse, and complete records. Row order and internal module layout may change. Zero-stock rows and empty results remain significant.

The evidence retains commands, raw outputs, expected normalized records, source identities, and endpoint rechecks. An expected rejection requires a nonzero exit, a diagnostic, and no report or archive output. The outcome keeps contract differences separate from observation failures. This bounded evaluator does not assess documentation, ordinary developer tests, review, or local commits; those remain separate completion evidence.

## Preparation package

```sh
python prepare_seed.py --spec SPEC.json --output NEW_PACKAGE
```

Version 1 has exactly five top-level fields: `version` (1), `seed`, `requests`, `observation_cases`, and `constructed_candidates`. Paths resolve relative to the specification. Each directory declaration has `path`, `files`, and `identity`. `files` is a nonempty, path-sorted list of `{path, sha256, executable}` entries. `identity` is SHA-256 over that list encoded as UTF-8 JSON with sorted keys, separators `(',', ':')`, and `ensure_ascii=False`. It identifies declared files only; unlisted files are omitted.

`requests` is an ordered list of `{path, sha256}` records. `observation_cases` adds a unique `id` to each such record. `constructed_candidates` contains unique `{id, source}` records, where `source` is a directory declaration. An empty candidate list prepares an ordinary seed without supplied variants. Input hashes and executable bits must match. Output must be new and separate from selected sources.

The package retains the exact `spec.json`, seed files, ordered requests, case files, and separately named candidate directories. `receipt.json` binds their hashes, byte counts, modes, directory identities, producer identity, and preparation timestamp. Its duration measures preparation through successful copy verification, excluding receipt serialization. `logical_bytes_read` counts selected input bytes, including the specification; it is not total physical I/O or a measure of operator effort. Copy failure after output allocation leaves `failure.json` when writable. Validation failures before allocation leave no package; preserve the command's diagnostic separately. Never overwrite a failed attempt to retry.

## Amendment collector mechanics

`collect_observation.py` prepares and runs one cooperative Python fake app-server observation. The first completed tool item observed after a change to a declared implementation file triggers one `turn/steer` request. A change only to a test file does not trigger it. Duplicate and later tool events cannot send a second amendment. The trigger records the observed file digests and item identity; it does not prove which event caused the change or provide a transactional filesystem snapshot.

```sh
python collect_observation.py prepare --seed-package PACKAGE \
  --seed-receipt-sha256 RECEIPT_SHA256 --profile PROFILE.json \
  --profile-sha256 PROFILE_SHA256 --implementation inventory.py --output NEW_OBSERVATION
python collect_observation.py run --manifest NEW_OBSERVATION/manifest.json \
  --expected-sha256 MANIFEST_SHA256
```

The seed package must be ready and contain exactly two ordered requests. Preparation binds the collector, seed producer, retained transport, selected seed files and modes, requests, profile, Python executable, and fake fixture. The ordinary fake profile has `kind: cooperative-python-fake/v1`, a `command` of the current Python executable followed by `-I`, `-S`, `-u`, and an absolute fixture path, and `python_sha256` and `fixture_sha256`. It is a declared cooperative fixture, not containment of arbitrary Python code. Only these cooperative Python fixtures can run.

The preparatory `cooperative-native-app-server-fake/v1` profile adds `app_server_profile`, containing `schema: compatibility-native-protocol-profile/v1` and an expected `version` string. It records the fake server's `initialize` response and compares its `userAgent` with that version before task delivery. A mismatch leaves an incomplete attempt with both values and the received response.

The metadata profile may also include both `model` and `effort`. After a matching version, this form sends `initialized` and requests `model/list` with hidden entries included. It requires list-valued catalog data containing one matching model and the requested effort. An omitted or null `nextCursor` permits that comparison; a non-null cursor stops it because paging is unfinished. An unavailable effort leaves the exact received catalog, expected and observed efforts, and an incomplete outcome without creating a thread or delivering a task. A version-only profile still stops after the version check.

With a matching model and effort, the native-shaped fake collects `config/read`, `configRequirements/read`, `skills/list`, and `mcpServerStatus/list` observations, then requests `thread/start` with the chosen model and provider fallback disabled. This is the collector's preparation sequence, not a mandatory native protocol order. A nonterminal MCP cursor leaves an incomplete attempt before thread creation. Config defaults may differ from the selected model or future turn effort; optional metadata remains absent or null as received. Discovery errors and unknown runtime status remain observations rather than an invented equipment-acceptance rule.

A matching thread model completes with `fake-profile-observed` by default. Its receipt links the effective profile to the retained response, records the requested future-turn effort separately, and leaves the turn ID null, amendment acceptance false, and semantic success `not-assessed`. A different reported model leaves an incomplete attempt with the returned thread ID and expected and observed models. Neither of these paths sends `turn/start` or task text. Thread metadata does not attest model execution or permission enforcement.

Setting the optional Boolean `app_server_profile.observe_turn` to `true` continues a matching native-shaped fake through the two prepared requests. The initial `turn/start` carries the selected model and effort explicitly. The first observed implementation-file change after a completed tool triggers one `turn/steer` for the same thread and turn. Rejected steering leaves an incomplete attempt with the original response; it does not start a replacement turn or retry. Successful steering and turn completion produce `fake-observation-completed`, while semantic success remains `not-assessed`. The default profile-only observation and ordinary fake behavior remain available.

The outcome's `usage_observations` indexes received `thread/tokenUsage/updated` receipts for the accounting reader. Records with both root identifiers and the required integer counter fields are separate from other thread/turn observations and malformed measurements. Counters remain in the original hash-bound wire records: repeated or decreasing snapshots are preserved, optional values are not filled, and no counters are added together. Malformed measurements do not alter task delivery. The collection boundary identifies the last received event and whether collection ended after root completion, profile observation, or an incomplete attempt. `whole_episode_tokens` remains null, including when no usage event was received. This index does not establish child relationships, complete capture after root completion, counter inclusion semantics, or billed usage.

After collection ends, `final_source` references `final-source.json` and an independent `final-source/` copy of the disposable project's regular files. The path-sorted inventory retains byte counts, hashes, modes, executable bits, its identity, thread/turn IDs, and the existing collection boundary. Capture includes added files and reflects removals; implementation selections govern amendment triggering only. It excludes `.git`, `__pycache__`, `*.pyc`, and `*.pyo`. Unsupported entries, filenames that cannot be represented in UTF-8, or copy/serialization failures mark capture `incomplete` while preserving the main observation. This cooperative-tree capture is not an atomic snapshot or adversarial containment. Deterministic completion-timing qualification remains follow-up; capture does not assess task quality or native readiness.

The local CLI regressions cover version and effort refusals, omitted and null model cursors, a nonterminal model cursor, completed fake profile observation with differing defaults and missing optional values, a nonterminal MCP cursor, a different returned thread model, and opt-in task delivery with accepted or rejected steering. The profile fixture follows the schema exported by Codex CLI 0.162.1; this is protocol-shape evidence, not observed account capability. Actual native profile discovery and task delivery remain unqualified.

Preparation and attempts require new destinations. The prepared manifest fixes a ten-second observation deadline. The existing transport retains up to 2 MiB of combined output and performs bounded owned-process shutdown; that shutdown can extend beyond the observation deadline. Raw sent bytes describe write attempts, not confirmed delivery. Ordered receipts reference retained inbound and outbound byte ranges, preserving the initial request, amendment, trigger, thread/turn IDs, and RPC outcome. An accepted steering RPC records only server acceptance. Semantic success remains `not-assessed` even when the fake turn completes.

A completed-turn race, rejected RPC, unanswered server input request, or observed dependency drift leaves an incomplete attempt when its destination is writable. Nothing automatically resends the amendment or starts another turn. Existing attempts cannot be overwritten. Validation failure before allocation leaves a diagnostic rather than an evidence package. Tests establish the selected successful sequence and these specific failures; malformed streams, abrupt EOF, deadline exhaustion, partial writes, and shutdown faults do not yet have distinct collector qualification.

Current native profile and protocol support, native event/file timing, permission handling, child histories and usage, required review capture, final behavioral grading, and whole-invocation accounting still need qualification before this collector can support an accepted native observation.

## Constructed contrasts and handoff

Each patch under `constructed/` applies independently to the seed using `git apply`. The four candidate identifiers carry no meaning for the consumer; the [construction record](constructed/README.md) describes their intended differences and the local checks that establish their effects. Keep that record and the tests outside judgment inputs.

Continue through the repo-carried `handling-sys1-incidents` [comparison contract](../../../../../.agents/skills/handling-sys1-incidents/references/comparison-contract.md). The next consumer must bind reviewed source, actual prepared packages, current requirements, amendment delivery, native profile and permissions, final grading, and complete cost accounting in a concrete execution contract. The behavioral comparator is an agent-visible aid only in its assigned arm; it is not the hidden final evaluator. The reviewed contract still requires execution acceptance. No native qualification, semantic classification benefit, publication, or live configuration change follows from these local checks.
