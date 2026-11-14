# Stable fork-versioning policy

Use this default when choosing a fork release version from an actual released, stable upstream baseline. The fork's checked-in policy remains authoritative where it deliberately differs. This policy does not define prerelease allocation or an independent major/minor compatibility policy for feature forks.

## Evidence before allocation

Identify the exact upstream release, tag, commit, and incorporated assets. Account for the candidate's differences from that baseline, including packaging-only changes. Record previous exposure in public releases and private or account-scoped deliveries, including versions since removed or withdrawn. Check whether candidate content differs from exposed content and whether each supported consumer can recognize the proposed version as an update. If the upstream baseline or exposure history is uncertain, return the missing evidence to its owner instead of allocating a version.

## Choose the version

- When the fork's numeric version equals the upstream version, use the plain version: upstream `4.8.0` can use `4.8.0`. This is permitted only when the exposure, changed-content, and update-precedence checks allow it.
- When the fork's numeric version differs, append the incorporated upstream baseline: for example, `4.8.1+from.4.8.0`.

For a fork-only advanced patch from upstream `M.m.U`, keep the upstream major/minor line and choose `M.m.P+from.M.m.U`, where `P` is one greater than the larger of `U` and the highest previously exposed fork patch in that line. On a higher major/minor line with no previous fork exposure, `P = U + 1`. A previously exposed version remains exposed even after its release is withdrawn. Do not reuse it for changed content.

For example, if `4.8.1+from.4.8.0` was exposed, a packaging correction can use `4.8.2+from.4.8.0`; a subsequent refresh to upstream `4.8.1` can use `4.8.3+from.4.8.1`. If an advanced patch is needed for a new `4.9.0` line with no prior exposure, it can use `4.9.1+from.4.9.0`. These examples assume the required evidence and checks; they do not allocate a release.

For changed content, the selected numeric version must advance beyond previously exposed packages in its release sequence. The numeric version supplies precedence; build metadata records upstream provenance and cannot by itself make a changed package an update. For example, an advanced release incorporating upstream `4.8.9` needs at least `4.8.10+from.4.8.9`, and a higher prior exposure can require a larger patch. Reuse one allocated full version across all supported formats and surfaces. A consumer-specific spelling requires demonstrated incompatibility; record the exception and qualify that consumer's update and migration behavior separately.

## Hand off the decision

Record the selected version or the unresolved input, the upstream identity, candidate content and exposure evidence, applicable fork-local exceptions, and consumer update checks. Give that record to the existing publication owner for the fork's normal review and release process. This policy does not authorize publication, change a version by itself, or establish a client's installation or update behavior.

For a vanilla repack, preserve upstream skill content and embedded versions while updating package-level manifests as required. The [Real Skills release procedure](https://github.com/nisavid/real-skills/blob/996d4b5115579d13f4b66a978b83581dd59bebda/docs/agents/release-archives.md) remains a fork-local advanced-patch contract; this default does not broaden that builder's supported inputs.

The [Fork Ops versioning decision](https://github.com/nisavid/fork-ops/issues/45#issuecomment-6690208453) owns the reusable default and its examples. The [Impeccable identity decision](https://github.com/nisavid/impeccable/issues/4) records a separate consumer's versioning and update-detection questions.
