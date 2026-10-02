# Correction to the preparatory route review's input provenance

I did not capture the eight input digests with the initial content read. I computed all eight in a separate, later inventory of live paths, after sending the two preparatory findings to the coordinator. The reports' statement that the table identifies the original reviewed bytes before coordinator amendments is therefore unsupported and, for the qualification contract, incorrect.

This note corrects the provenance claim in `implementation-route-review.md` (full-file SHA-256 `715b4b8fe8d795743d917585f7ebf6a658529a00e00f55b5373b8904a2bab834`) and its path-normalized publication edition, `implementation-route-review-public.md` (full-file SHA-256 `4b50625a50a1f905bdd156fcc2d6f87a9b6f6ec130acbee804bc99c80a09e9aa`). Both files remain unchanged.

## What the execution evidence establishes

The initial content read and the later numbered-text read showed a qualification contract without the paragraph assigning each obligation to a source, deployment, or fresh-invocation phase. The digest inventory was a subsequent operation that reopened each live file. It did not hash a retained copy of the bytes returned by either earlier read.

I now verified that `implementation-map/qualification-contract.md` is 2,324 bytes and has SHA-256 `a64cd79887198337083f8b3f675705a76055ac5b9d862deb90dfe4cf327971c3`. Its content includes the added phase-ownership paragraph. That table entry thus identifies corrected bytes already present during the later inventory, not the initial qualification-contract content on which the finding was based. The later arrival of the coordinator's amendment message did not establish when the shared file changed.

All table entries must be read as **later inventory identities**:

| Logical input | Later inventory SHA-256 |
| --- | --- |
| `implementation-map/map.md` | `4acca33d5c2a564ad3ac01ce20fc0a664f8c1ae2917324708921952c5f4ffde2` |
| `implementation-map/source-contract.md` | `7d27e614a4e3fc8ab744ce4396eb4c8876f7cc79067e1ce4e5601d46397f5d67` |
| `implementation-map/qualification-contract.md` | `a64cd79887198337083f8b3f675705a76055ac5b9d862deb90dfe4cf327971c3` |
| `implementation-map/implementation.md` | `a61405f87dc11eb0f869a42920a652346a44a06200be198fba702352480bf479` |
| `implementation-map/publication-deployment.md` | `8de587045602595d566a00ff24ec2cf7d7cd4bf32a48cb9d27b7b895921da581` |
| `implementation-map/consumer-invocation.md` | `f347a38cca3919258717fb9ee10c7f3e538b3d661b3a8a16c5b5e1bbd2f2e66d` |
| `architecture/comparison.md` | `414a83d824326a94afb2e6f492153a8bff28038ad4ed19d80b420e17ff31027d` |
| `architecture/packaging-feasibility.md` | `563c1feb380565ea0ad32fc6d1d8b9d46a7f347bd90e30575ddaa4bc8b9eb52b` |

`implementation-map/<file>` retains the publication edition's logical identity for the original scratch input `map-drafts/<file>`. `architecture/<file>` abbreviates the corresponding file under `docs/superpowers/research/2026-10-01-repository-configuration/architecture/` in `nisavid/provingkit`.

None of these digests independently establishes the initial-read bytes. I did not preserve immutable initial file snapshots or compute initial-read digests, and I cannot establish a complete original byte manifest from the evidence this review retained. The other seven entries may coincide with the earlier content, but this note makes no such claim. I have not reconstructed missing original bytes from memory.

The preparatory findings remain observations about the earlier text returned by the content reads. They must not be treated as a review or rejection of the later inventory's complete byte set. This correction does not review the corrected route's substantive coverage and does not supply final acceptance.
