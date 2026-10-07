# Prepare claim and publication evidence for comparison

These local research CLIs produce source-preserving evidence packages for the [claim-support and publication-coverage proposals](../jev-axi-comparison-preparation-2026-10-07/README.md). They perform no model calls, semantic assessment, publication, or live-hook changes. The [comparison design](comparison-design.md) includes the requested Luna, Sol, Decisions, and Jev alternatives and endpoint-specific accounting.

## Run the retained examples

From the repository root, choose new output directories whose parents already exist:

```sh
task_output=$(mktemp -d)
python docs/superpowers/research/evidence/jev-axi-comparison-producers-2026-10-07/claim_producer.py prepare-claim --repository . --case-spec docs/superpowers/research/evidence/jev-axi-comparison-producers-2026-10-07/examples/claim-retained.json --output "$task_output/claim-evidence"
python docs/superpowers/research/evidence/jev-axi-comparison-producers-2026-10-07/coverage_producer.py prepare-coverage --repository . --case-spec docs/superpowers/research/evidence/jev-axi-comparison-producers-2026-10-07/examples/coverage-retained.json --output "$task_output/coverage-evidence"
```

The selected historical Git objects must be present locally. The claim example preserves the original assertion and its complete sources. The coverage example describes the nine-file commit candidate: seven content identities match, two supporting records are absent from the content map, and the separately recorded review digest matches. Those relationships do not establish an actual push range or review completeness.

Each new directory contains `packet.json`, a readable `packet.md`, raw source/candidate files, and `receipt.json`. Receipts bind producer and case-spec bytes, artifact digests, acquisition counters, and preparation duration. A ready package is mechanically usable within the producer's supported input shape; it is not a true-claim or publication-ready verdict. Existing output directories are refused without changing their files.

## Claim input

The version-1 case spec supplies a neutral case ID, exact assertion, optional direct quotation, one draft reference, and one or two ordered source references. References carry a full SHA-1 commit ID, repository-relative path, and expected SHA-256. The draft additionally specifies one-based start, end, and assertion line numbers. Its context includes the designated assertion; the caller selects the enclosing context and citations.

The producer retains complete source bytes and checks expected identities. Literal quotation matching normalizes only line endings; it does not normalize Unicode, establish semantic support, or identify fabricated text. A source can declare `availability: controlled_unavailable` for the constructed retrieval-failure case. That status remains distinct from a real missing object. No semantic request should consume a non-ready packet.

Supported source entries are UTF-8 regular files, including executable files. Mutable revisions, malformed specs, unsupported entry types, missing objects, changed source bytes, and invalid context are non-ready. Exit 0 indicates ready evidence; exit 2 indicates non-ready input or an existing output. An unhandled local I/O failure can leave a partial directory and a nonzero process result; preserve it rather than retrying into the same directory.

## Coverage input

The version-1 spec supplies full parent and child commit IDs, ordered source references, and indexes identifying the verification record and review. The child must directly name the parent. The supported record schema has `reviewed_public_inputs`, mapping repository-relative paths to SHA-256, and a separate `review_sha256`.

The producer preserves the parent-to-candidate path/mode/blob inventory and complete resulting difference bytes. It reports equal, different, absent, or unavailable relationships, plus map entries outside the difference. Unavailable records never become absent membership. A mismatch between an intact candidate and an intact record is a ready mechanical relationship. A supplied source failing its expected identity is non-ready.

Optional `overlays` provide complete base64 replacement/addition bytes and regular-file modes. Their results are derived snapshots with a full path/mode/blob inventory digest, not historical commits. Construction directives stay in the case spec, outside the consumer packet. Snapshot identity does not claim that its calculated Git object IDs exist in the repository. File/directory collisions are rejected.

The initial scope excludes deletions, symlinks, submodules, semantic rename detection, arbitrary push ranges, and review applicability. Unsupported changed entries remain visible and make the package non-ready. Exit 0 indicates a ready relationship package; exit 2 indicates non-ready inputs; exit 1 indicates output allocation/write failure.

## Verification and measurement limits

```sh
python -m unittest discover -s docs/superpowers/research/evidence/jev-axi-comparison-producers-2026-10-07 -p 'test_*_producer.py'
```

Tests exercise the operator-confirmed CLI and output-package boundaries with disposable Git fixtures. They cover exact source preservation, changed/missing input, source ordering, literal quotation handling, malformed records, derived snapshots, separate review identity, mode changes, unsupported entry types, and existing-result preservation.

Acquisition counters describe the bytes each implementation reports, not physical filesystem I/O or model tokens. Preparation durations end before receipt writing completes; external invocation timing is needed for the complete wall interval. Receipt hashing and other omitted work are not measured as source-read bytes. Keep these distinctions when comparing standalone and shared preparation. No native benefit, model reliability, quota, money, or operator savings is established by these local checks.

## Maintained consumer

This preparation invokes `handling-sys1-incidents` and its [comparison contract](../../../../../.agents/skills/handling-sys1-incidents/references/comparison-contract.md). It is project-local research equipment. The producer boundary and runnable examples provide the consumer handoff required by `capturing-agent-procedures`; the maintained skill is unchanged. Example invocation demonstrates preparation only, while downstream experimental use remains separate evidence.

The next contract author must bind the reviewed producer revision, cases, question definitions, evaluator separation, actual model routes, accounting, and stopping behavior. Changing any material input invalidates affected evidence. Both ordinary contracts require review and execution acceptance before model trials.
