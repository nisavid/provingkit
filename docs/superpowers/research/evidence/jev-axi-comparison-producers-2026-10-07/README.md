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

The producer retains complete source bytes and checks expected identities. The designated assertion must occur exactly once in the selected draft context. A ready result also contains `inference.json`: only `assertion`, `draft_context`, and ordered `sources` with neutral `id` and complete `text`. Decoding and JSON escaping preserve the UTF-8 source text and its line endings; no numbered Markdown reconstruction or semantic summary supplies this projection. Its digest and length appear in the receipt. Non-ready results emit no inference file. Provenance and acquisition status stay in the separate evidence package.

Literal quotation matching normalizes only line endings; it does not normalize Unicode, establish semantic support, or identify fabricated text. A source can declare `availability: controlled_unavailable` for the constructed retrieval-failure case. That status remains distinct from a real missing object. No semantic request should consume a non-ready packet.

Supported source entries are UTF-8 regular files, including executable files. Mutable revisions, malformed specs, unsupported entry types, missing objects, changed source bytes, and invalid context are non-ready. Exit 0 indicates ready evidence; exit 2 indicates non-ready input or an existing output. An unhandled local I/O failure can leave a partial directory and a nonzero process result; preserve it rather than retrying into the same directory.

## Saved draft input

On Linux, version 2 accepts a preserved working draft and one explicitly linked report. It keeps the version-1 command and committed-input behavior. Use this path when a draft has been saved but committing it would interrupt ordinary authoring.

1. Preserve the complete UTF-8 draft and selected report as regular files beside the case spec, retaining their original repository-relative locations and named checkpoints. Select the original assertion and enclosing qualifications without rewriting either. The caller is responsible for choosing sufficient context and making the copies; the producer does not observe the author or attest capture time.
2. Supply the version-2 fields illustrated by [the snapshot example](examples/claim-snapshot.json). Each snapshot reference has `kind: snapshot`, `path` (original location), `snapshot` (copy location relative to the spec), `checkpoint` (1–64 letters, digits, underscores, or hyphens), and `sha256`. A snapshot has no `commit` field. The report may instead use the existing committed reference. Paths to copies have no absolute, empty, dot, or parent components; symlinks and nonregular copies are unsupported. The spec's directory is the caller-selected input root.
3. Set `source_link.line` within the selected draft context and `source_link.target` to the explicit local Markdown target. The target must resolve from the draft's original location to the report's original path. The initial grammar accepts one inline `[label](relative-path)` on a plain prose line; targets use letters, digits, underscores, hyphens, dots, and slashes, including parent segments. It excludes reference links, URLs, fragments, escaped or nested brackets, images, indented/quoted code, and inline code. As a conservative limitation, HTML or fence markers anywhere before that line also make the link unresolved. This checks the literal association; it is not a full Markdown renderer or a judgment about source faithfulness.
4. Run the existing command with a new output directory. For the supplied synthetic example:

   ```sh
   task_output=$(mktemp -d)
   python docs/superpowers/research/evidence/jev-axi-comparison-producers-2026-10-07/claim_producer.py prepare-claim --repository . --case-spec docs/superpowers/research/evidence/jev-axi-comparison-producers-2026-10-07/examples/claim-snapshot.json --output "$task_output/evidence"
   ```

5. Consume `inference.json` only after exit 0 and a ready packet. It preserves the same assertion/context/complete-source projection as version 1. Provenance remains in `packet.json`, including the original locations, checkpoint names, expected/observed hashes, link association, and raw-copy paths. A ready result means the supplied bytes and literal association match; sufficient qualifications, historical truth, timely delivery, and semantic fidelity still require their own evidence.

If a copy is missing, changed, unsupported, or associated with a different report, preserve the non-ready package and omit any semantic request. Refresh into a new directory with newly selected identities. An intentional amendment can carry `supersedes: {"checkpoint": "prior-checkpoint", "sha256": "prior-digest"}`; both must differ from the new identity. This is a caller-declared relationship, retained separately from inference, not a verified lineage or an automatic search for later reports. Preserve the earlier package and state that the later question concerns the amended report. The producer never silently updates the expected identity or substitutes a newer source.

Receipts keep `git_blob_bytes_read` separate from `snapshot_bytes_read`, `snapshot_read_attempts`, and `git_commands`. Byte counters measure complete returned input buffers; operation counters count attempted snapshot acquisitions and launched Git commands, not kernel reads. Missing/unsupported snapshot attempts still count. Hashing, copying the inputs before invocation, choosing the assertion/context, and consuming the output remain additional work. Measure complete invocation elapsed time outside the process, from launch through its exit; `duration_monotonic_ms` still ends before the receipt write. No token, monetary, quota, or total operator cost is inferred.

## Coverage input

The version-1 spec supplies full parent and child commit IDs, ordered source references, and indexes identifying the verification record and review. The child must directly name the parent. The supported record schema has `reviewed_public_inputs`, mapping repository-relative paths to SHA-256, and a separate `review_sha256`.

The producer preserves the parent-to-candidate path/mode/blob inventory and complete resulting difference bytes. It reports equal, different, absent, or unavailable relationships, plus map entries outside the difference. Unavailable records never become absent membership. A mismatch between an intact candidate and an intact record is a ready mechanical relationship. A supplied source failing its expected identity is non-ready.

Optional `overlays` provide complete base64 replacement/addition bytes and regular-file modes. Their results are derived snapshots with a full path/mode/blob inventory digest, not historical commits. Construction directives stay in the case spec, outside the consumer packet. Snapshot identity does not claim that its calculated Git object IDs exist in the repository. File/directory collisions are rejected.

The initial scope excludes deletions, symlinks, submodules, semantic rename detection, arbitrary push ranges, and review applicability. Unsupported changed entries remain visible and make the package non-ready. Exit 0 indicates a ready relationship package; exit 2 indicates non-ready inputs; exit 1 indicates output allocation/write failure.

## Verification and measurement limits

```sh
python -m unittest discover -s docs/superpowers/research/evidence/jev-axi-comparison-producers-2026-10-07 -p 'test_*_producer.py'
```

Tests exercise the operator-confirmed CLI and output-package boundaries with disposable Git fixtures. They cover exact source preservation, changed/missing input, source ordering, literal quotation handling, saved-draft associations and amendments, malformed records, derived snapshots, separate review identity, mode changes, unsupported entry types, and existing-result preservation.

Acquisition counters describe the bytes each implementation reports, not physical filesystem I/O or model tokens. Preparation durations end before receipt writing completes; external invocation timing is needed for the complete wall interval. Receipt hashing and other omitted work are not measured as source-read bytes. Keep these distinctions when comparing standalone and shared preparation. No native benefit, model reliability, quota, money, or operator savings is established by these local checks.

## Maintained consumer

This preparation invokes `handling-sys1-incidents` and its [comparison contract](../../../../../.agents/skills/handling-sys1-incidents/references/comparison-contract.md). It is project-local research equipment. The producer boundary and runnable examples provide the consumer handoff required by `capturing-agent-procedures`; the maintained skill is unchanged. Example invocation demonstrates preparation only, while downstream experimental use remains separate evidence.

The next contract author must bind the reviewed producer revision, cases, question definitions, evaluator separation, actual model routes, accounting, and stopping behavior. Changing any material input invalidates affected evidence. Both ordinary contracts require review and execution acceptance before model trials.
