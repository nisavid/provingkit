# Prepare an inventory compatibility comparison

This fixture supplies an ordinary inventory-report task, real consumers, a behavioral comparator, and a producer that preserves declared preparation inputs. It supports the [compatibility observation preparation](https://github.com/nisavid/provingkit/issues/471). It does not run a native agent or establish a useful role for Jev or `jev-axi`.

The [workload proposal](../jev-axi-compatibility-workload-preparation-2026-10-07/README.md) defines the consumer purpose and comparison. The baseline repository is `seed/`; its README and tests are ordinary developer inputs. Ordered task requests live in `requests/`, and input selections live in `cases/`. Keep this README, constructed patches, construction notes, and preparation tests outside a native worker's seed. They contain evaluation information.

## Local checks

Run from this directory:

```sh
python -m unittest discover -s seed/tests -v
python -m unittest discover -s . -p 'test_*.py' -v
```

The approved test interfaces are the report and consumer CLIs, the before/after comparison CLI, and the preparation CLI with its evidence package. Tests use disposable files and a local Git patch operation. They make no provider request. Constructed changes are fixtures, not evidence that an ordinary agent would make those mistakes.

## Behavioral comparison

```sh
python compare_behavior.py --before BEFORE --after AFTER \
  --input INVENTORY.json --output NEW_EVIDENCE --warehouse South --threshold 2
```

Use trusted, cooperative local source directories on a POSIX host. The comparator invokes each report and consumer with the current Python executable, retains the input bytes, command arguments, exit status, stdout/stderr bytes and display text, archive bytes, and normalized records. It compares records as multisets; row order is not a compatibility requirement. It checks both unfiltered and selected-warehouse reports when `--warehouse` is supplied. Low-stock and archive consumers keep their existing unfiltered invocation.

Exit 0 means observed compatibility, exit 1 means a behavioral difference, and exit 2 means an observation failed or invocation was invalid. A command failure cannot establish compatibility. The summary preserves differences at other successful boundaries even when its overall outcome is `observation_failed`. A malformed successful report is a difference. These outcomes describe the selected observations, not every possible input or the JSON addition's full correctness.

Each command has a five-second deadline. On timeout, the comparator kills its owned process group and retains partial output. This provides cooperative resource cleanup, not containment of hostile programs. Source identities hash files under each supplied directory except Python cache files; supply the intended source snapshot, not an unrelated checkout. Evidence output must be outside both source directories; existing evidence directories are refused.

## Preparation package

```sh
python prepare_seed.py --spec SPEC.json --output NEW_PACKAGE
```

Version 1 has exactly five top-level fields: `version` (1), `seed`, `requests`, `observation_cases`, and `constructed_candidates`. Paths resolve relative to the specification. Each directory declaration has `path`, `files`, and `identity`. `files` is a nonempty, path-sorted list of `{path, sha256, executable}` entries. `identity` is SHA-256 over that list encoded as UTF-8 JSON with sorted keys, separators `(',', ':')`, and `ensure_ascii=False`. It identifies declared files only; unlisted files are omitted.

`requests` is an ordered list of `{path, sha256}` records. `observation_cases` adds a unique `id` to each such record. `constructed_candidates` contains unique `{id, source}` records, where `source` is a directory declaration. An empty candidate list prepares an ordinary seed without supplied variants. Input hashes and executable bits must match. Output must be new and separate from selected sources.

The package retains the exact `spec.json`, seed files, ordered requests, case files, and separately named candidate directories. `receipt.json` binds their hashes, byte counts, modes, directory identities, producer identity, and preparation timestamp. Its duration measures preparation through successful copy verification, excluding receipt serialization. `logical_bytes_read` counts selected input bytes, including the specification; it is not total physical I/O or a measure of operator effort. Copy failure after output allocation leaves `failure.json` when writable. Validation failures before allocation leave no package; preserve the command's diagnostic separately. Never overwrite a failed attempt to retry.

## Constructed contrasts and handoff

Each patch under `constructed/` applies independently to the seed using `git apply`. The four candidate identifiers carry no meaning for the consumer; the [construction record](constructed/README.md) describes their intended differences and the local checks that establish their effects. Keep that record and the tests outside judgment inputs.

Continue through the repo-carried `handling-sys1-incidents` [comparison contract](../../../../../.agents/skills/handling-sys1-incidents/references/comparison-contract.md). The next consumer must bind reviewed source, actual prepared packages, current requirements, amendment delivery, native profile and permissions, final grading, and complete cost accounting in a concrete execution contract. The behavioral comparator is an agent-visible aid only in its assigned arm; it is not the hidden final evaluator. The reviewed contract still requires execution acceptance. No native qualification, semantic classification benefit, publication, or live configuration change follows from these local checks.
