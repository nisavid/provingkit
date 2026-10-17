# Prepare an offline writing evaluation

Freeze the writer corpus, its instructions, and three repetitions from one
committed revision before assigning any model execution.

Run from the selected checkout:

```sh
python scripts/prepare_proseweaving_eval.py prepare --repository . --source-revision FULL_COMMIT_OID --output-dir NEW_PRIVATE_DIRECTORY
```

Run on a POSIX host with directory file descriptors, no-follow opens, and hard
links. Windows execution is unsupported. The output parent must already exist,
and the output leaf must be new. The executing preparer and bootstrap transport
must match the selected commit; the remaining helpers load from that commit. The writer corpus is enumerated; the command
supports only `writing-for-people` and repetitions 1–3. Twenty-eight cases yield
84 unstarted coordinates. This prepares explicit input delivery; it establishes
no native discovery, tool isolation, model behavior, or release qualification.

## Retained files

- `source/<repository-relative-path>` preserves the method, its declared local
  import helpers, this procedure, and Proseweaving input files.
- `source-inventory.json` binds their Git modes, byte counts, and SHA-256 digests.
  Private copy modes and host runtime identity are recorded separately.
- `requests/case-001.json` and its peers contain only `prompt`, `fixture`, and
  `candidate_bundle`, in that order. Bundle keys are sorted logical paths.
- `grading/case-001.json` and its peers contain `expected_output` and
  `expectations`. They contain no response and are not grader executions.
- `coordinates.json` binds every case and repetition to its request, with state
  `unstarted`. Repetitions share immutable request bytes; later executions still
  require separately authorized fresh sessions.
- `preparation.json` records `prepared-not-executed`, the source commit, selected
  writer, coordinate count, and exhaustive payload/source inventory.
- `outcome.json` identifies the preparation by digest and records its outcome,
  diagnostics, and intended exit code. Complete stdout has these same bytes.

JSON is UTF-8 with a terminal LF, no indentation, finite numbers, and no duplicate
keys. Actor fields retain builder order. Other records use the existing
canonical sorted-key serializer; arrays retain order. Digests cover exact bytes
including LF and use lowercase SHA-256 hexadecimal without a prefix. Directories
are 0700 and files 0600. Original Git modes identify source files, rather than
prescribing private-copy permissions.

The preparation inventory excludes itself and the later outcome to avoid a
self-digest cycle. The outcome identifies the preparation; consumer readback
checks the whole graph and the complete directory shape.

## Acceptance

Capture complete stdout, stderr, and the actual process return code. Exit 0 is
reserved for complete; 1 means unfinished or uncertain; 2 means rejected input
or usage. A missing outcome is unaccepted even if some files remain.

Load the preparer from the same reviewed revision and use its documented
consumer boundary:

```python
verify_preparation(
    output_dir, repository=selected_repository, source_revision=selected_commit,
    stdout=captured_stdout, returncode=actual_returncode,
)
```

The repository and commit are independently selected expected inputs, not values
admitted from the candidate packet. This raises `PreparationError` unless the
observed outcome, source/method identity, every retained file's bytes and modes, expected directory shape,
actor/grading separation, and complete case/repetition coverage agree. A
complete flag or intended exit code alone cannot establish acceptance.

The command reuses the existing Proseweaving builders and evidence transport.
Its source selection never traverses other plugins. It reads Git objects rather
than working-tree inputs and rejects unsafe paths, links, submodules, missing
inputs, abbreviated revisions, and mismatching runtime method/helper bytes.
The declared method and inputs coexist in one selected commit; the separate
Mergecraft feedback controller is not a dependency.

Private immutable publication refuses differing existing bytes. Existing output
is rejected unchanged. Failures after reservation retain partial evidence and an
unsuccessful outcome where possible. Do not repair or retry an output in place.
Readback establishes ordinary cooperative byte correspondence, not adversarial
attestation, arbitrary crash durability, a hermetic runtime, or host-wide
process isolation.

## Development and downstream use

Run `python -m unittest tests.test_proseweaving_eval_preparation` for controlled
local Git/filesystem checks. They use independent literal actor expectations and
public command/consumer interfaces; they do not launch a harness or model.

A consumer records the reviewed procedure and source revision, observes its
actual invocation, verifies all referenced outputs, and returns failures or
limits to this maintained procedure. Source implementation and tests remain
separate from independent review, publication, actual behavioral execution,
baseline acceptance, installation, and release qualification.
