# Addendum: preparatory review provenance correction

The preparatory route review does not bind its initial content reads to the eight hashes it labels as original input identities. My original audit's unqualified conclusion that there was no actionable evidence defect was too broad for that provenance claim. This addendum corrects that part of the audit; the independently checked current map bodies and retained snapshot remain unchanged.

## Correction and its effect

I read the route author's correction note, `route-review-provenance-correction.md`, and verified its full-file SHA-256 as `85b6e6eb6d53a82e4cf839512ee97d44ad7a959eefe1bb61bbb311cc161d51fc`. The author states that all eight input digests were computed by reopening live paths after the initial findings, without retaining the initial read bytes or hashing those bytes at read time. Each entry is therefore a later inventory identity. None independently establishes the initial-read input, and the complete original byte set cannot be reconstructed from the retained evidence.

The qualification-contract entry is demonstrably the current corrected file: 2,324 bytes, SHA-256 `a64cd79887198337083f8b3f675705a76055ac5b9d862deb90dfe4cf327971c3`, including the paragraph assigning obligations to source/pre-deployment, publication/installation, and fresh-invocation phases. The author's note reports that this paragraph was absent from the earlier content reads. The other seven hashes may coincide with earlier content, but neither the note nor this addendum establishes that.

The affected retained report is `docs/superpowers/research/2026-10-01-repository-configuration/architecture/reviews/implementation-route-preparatory.md`, SHA-256 `4b50625a50a1f905bdd156fcc2d6f87a9b6f6ec130acbee804bc99c80a09e9aa`. Its claims that the table identifies original reviewed bytes before amendments are unsupported. Its findings remain the author's observations about earlier returned text; they must not be represented as a review or rejection of the complete later inventory. I did not inspect the author's execution transcript or recover missing original snapshots.

Keep the original preparatory report and audit unchanged, and retain the correction note and this addendum with them. When citing that preparatory review, identify its hashes as later inventory and make the missing initial byte binding explicit. Do not manufacture replacement original hashes. The correction supplies no acceptance of the amended route.

## What I reverified

I parsed the original audit's 31-file inventory and recomputed every listed file's full digest and byte count. All 31 still match, including the preparatory report. I also rechecked that each of the six current implementation body files matches both its digest in `implementation-map/index.json` and the corresponding body string in `implementation-map/initial-graph.json`. The recorded blocker sets and complete pagination flags still agree with the index.

These are the key retained identities, with paths relative to `docs/superpowers/research/2026-10-01-repository-configuration/architecture/`:

| Input | SHA-256 |
| --- | --- |
| `implementation-map/index.json` | `7640677a237fef2783fe4531ff767ef59b61c9f14eaca1161cddca938e75e1e7` |
| `implementation-map/initial-graph.json` | `3382c20428b0921299bb935afe4eaaaa6e1d2d08a37b735602dcfb052a817879` |
| `implementation-map/qualification-contract.md` | `a64cd79887198337083f8b3f675705a76055ac5b9d862deb90dfe4cf327971c3` |

My prior substantive reading of the corrected route was bound to those current files in my own inventory. It did not rely on the preparatory review's table as proof of the corrected candidate. The corrected source/pre-deployment, deployment, and fresh-invocation division therefore remains within the scope of my original evidence check. The frozen architecture proposal/exchange checks also remain valid; this correction concerns the separate preparatory review's initial-read provenance.

The graph verification concerns the retained charting snapshot only. I did not query current GitHub state. This addendum does not extend the original review to other files appended to the architecture directory.

## Readset, preservation, and limits

The original audit, `design-evidence-audit.md`, remains 20,531 bytes with SHA-256 `795e5aafd65f7b0473283332c4497921ff1798696805102d7712f5ea184e04a5`. I read the correction note in full, used the original audit's complete inventory, reread the current qualification contract, and performed byte and structural comparisons across that inventory and the implementation index/snapshot. The original audit retains the full paths and digests for all 31 inputs. I did not renew the separate immutable-source or external-platform research checks in this follow-up.

No network, source, tracker, installed-state, or Git mutation ran. Only this addendum was written. It was prepared on 2026-10-02 UTC. Architecture, packaging, live qualification contexts, and local client targets still require the actual human choices, followed by review of the final candidate. This remains preparatory evidence, not final design acceptance.
