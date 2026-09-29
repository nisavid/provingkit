# Authorize one disposable observer probe

Use this checklist in the authorization ticket after independent review of the
candidate. Record accepted or amended terms in the user's own decision. A
source review or completed preparation ticket supplies no live grant.

| Scope | Terms to confirm |
| --- | --- |
| Source and application bytes | Published procedure/source revision; generated `build-receipt.json` tied to the proposed archive; published `candidate-build.json`; mandatory byte-for-byte comparison between them; exact archive, manager, and sidecar digests from that receipt; exact reviewed archive-verification path and SHA-256, bound to the private record and freshly compared with the actual record bytes at preflight and every repeated receipt or archive-evidence check |
| App changes | Temporary replacement of the inspected installed archive, preserving executable, native assets, launcher, and sandbox layout; close before staging, close before restoration, and launch after each exchange |
| Operating window | One scheduled window using the current signed-in profile; two full shutdown/launch cycles, two exact setup prompts, and the listed manual preflight and restoration checks; getter initiation, asynchronous waiting, and settlement acceptance use one 30-second monotonic observation deadline, without a hard-cancellation or total-duration claim; total duration remains an unmeasured scheduling unknown |
| Failure control | Keep a manual phase supervisor outside the `set -euo pipefail` shell; on failure or shell exit, preserve the earliest failure, stop collection, establish Desktop quiescence, and re-enter only the already authorized restoration cycle through a fresh shell reconstructed from the immutable reviewed definitions and existing private binding record; no failed-actuation retry, extra private read, restoration across upgrade or drift, silent grant expansion, additional candidate cycle, or extra restart; when the authorized autonomous control surface is unavailable, return to the human operator |
| Launcher | Exact launcher path, SHA-256, device, inode, owner, group, mode, link count, and size; root-owned non-writable ancestors; exact NUL-delimited argument-file path, identity, and reconstructed byte digest; stable-descriptor validation immediately before both launches |
| Fixture | One new top-level local Code task named `Desktop observer probe 278`, created through the normal new-task UI in a new dedicated empty non-Git directory; never fork, spawn, import, duplicate, or reuse; do not resolve or invent a worktree before creation; if Desktop creates one, bind its identity and exact expected app-managed entries; bind the actual profile, account, organization, task ID, Code ID, real directory identities, Electron app-data root, the concrete `claude-code-sessions` base, and the constructed metadata path before staging; never call internal `getSessionFilePath` |
| Fixture isolation | Project only the normative selected-fixture fields from the selected file; require `cwd` to match the dedicated project and preserve each optional path as absent, empty, or an approved nonempty real-directory identity; preserve optional-lineage presence, stop on a non-null relation or true `lineageDetached`, and do not convert absence into confirmed nonrelation; record local creation from normal UI provenance and keep the static local-backend guard as separate source evidence; stop on any path, identity, directory-shape, or activity discrepancy; record `selectedMetadataRelations` as `no-nonnull-relation-observed`, `globalChildAbsence` as `not-established-from-selected-metadata`, and `unrelatedSharingAbsence` as `not-established` |
| Setup | Two submissions of the exact `PROBE_READY` prompt in the procedure, one before staging and one afterward, on that fixture only |
| Local configuration | One exclusively created private configuration outside a new private run directory; deterministic canonical UTF-8 bytes with no BOM or final newline; exact selected paths, task and Code IDs, receipt candidate and module hashes, 60-second setup deadline, and 100-millisecond setup polling |
| Arm and getters | Validate the selected bootstrap before arm; record every generated binding value; exclusively create one canonical UTF-8 arm that echoes every `BINDING_KEYS` field, including `monotonicClockId` and `linuxBootId`; accept it within 60 seconds of bootstrap; three sample initiations at least five seconds apart; getter initiation, asynchronous waiting, and settlement acceptance bounded by one 30-second monotonic observation window; the three named getters sequentially with waits of at most two seconds each and clamped to the remaining window; no hard cancellation claim for uncancellable or synchronously blocking work; no retry after terminal failure |
| Receiver data | The procedure's named provider/model, rules/directory grants, account IDs, host settings/grants, cwd, and Code process/version report; no prompt/transcript, credential, environment, or raw-error export |
| Linux process observation | One separately invoked observation sourced from a freshly validated sample with matching before/after reports; one read of the single nonsecret Linux boot-ID path `/proc/sys/kernel/random/boot_id` for each of the initial and final sample acquisitions; bind monotonic timestamps to `linux-clock-monotonic.v1` and that boot ID; pass explicit fresh wall and monotonic clock values to direct `readProbeSample` or `inspectProbeSample` calls; two selected-PID path metadata checks and one owned `O_DIRECTORY | O_NOFOLLOW` descriptor open; seven descriptor metadata checks, including owner, identity, and fresh wall and monotonic limits immediately before each child open; child resolution only through the retained descriptor; three `stat` opens reading at most 4,096 bytes each; two opens of `exe`; at most 256 MiB hashed; no PID-path child re-resolution, enumeration, or alternate PID |
| State changes | No deliberate account, model, permission, grant, or cwd transitions; stop for a separately reviewed proposal if one becomes necessary |
| Retained Linux result | Use the invocation, wrapper, and result variants defined normatively in `private-data-contracts.md`; invoke the helper at most once and only from an actual usable selected sample; preserve the producer's actual result status and gaps, including `unavailable` gaps for missing or null `cliPidAtMs` and `cliReportedVersion`; preserve either field independently as its actual value or JSON `null`; null neither proves runtime knowledge nor requires invention, gap suppression, or rejection or reclassification of a valid `observed-partial` helper result; use the strict sample reader, which requires every `UNKNOWN_CLAIMS` value and the unqualified outcome; serialize only a validated wrapper to the bound private `selected-linux-executor-observation.json`; if no usable sample exists, do not call the helper; record the exact applicable absent reason from the normative cleanup schema and do not retry merely to fill the manifest |
| Retention | Keep every actually created private output, any valid retained Linux-observation file, every unresolved or possibly created private resource, and the private cleanup manifest through the issue 281 decision; remove only the exact private subset later approved from a reviewed manifest |
| Package cleanup | Treat package cleanup as a distinct pre-manifest phase; only after verified restoration, remove at most the exact staging archive, protected backup, and empty backup run root in order; immediately before each file deletion, use the shared archive check to require the bound digest, expected size, `root:root`, mode `0644`, one link, base ACL only, no xattrs, regular-file type, and no symlink, then perform the existing comparison and absence checks; record each resource as known, uncertain, removed, or absent; preserve the earliest failure and stop without retry on a failed or partial removal; no package deletion after incomplete, not-required, or otherwise unverified restoration |
| Cleanup inventory | Use only the `provingkit.desktop-probe-cleanup.v2` schema in `private-data-contracts.md`; create it after package cleanup ends or, when package deletion is prohibited, at the terminal stop; record exact status, restoration, package-cleanup, fixture, output, retained-evidence, and resource-role tokens; record retention only in the nested `restoration.recoveryRecord.retention` and `fixture.retention` fields; list only actual validated files and established resource states; never fabricate a task ID, Code ID, metadata path, binding, sequence, helper result, file identity, or package-removal result; incomplete restoration requires the recovery record, retention of all package and private artifacts, and no deletion |
| Task cleanup | Revalidate the selected metadata and current coordination, then use only the normal exact-task Desktop UI; require its confirmation to establish the managed scope, including linked-task and worktree effects, as matching the fixture; accept managed removal of that task's transcript and dedicated worktree; do not call internal deletion or family APIs or scan all tasks; retain the fixture if the control or scope cannot be established |
| File cleanup | Unlink only individually approved manifest-listed user-owned files after exact identity and containment checks; use `rmdir` only for verified empty owned directories; no globs, recursive removal, manual private-store or transcript deletion, or unrelated-worktree changes |
| Restoration | Restore verified pristine package bytes, recheck protected assets, launch without the observer binding, and check application and recorded work expectations separately |

Bind the concrete paths, package metadata, receipt identities, launch arguments,
staging, cleanup-manifest path, and restoration steps from
[application staging and restoration](application-operation.md) in the private
approval packet. Use [private probe data contracts](private-data-contracts.md)
for the normative selected-fixture projection, selected-executor invocation and
result variants, and cleanup manifest. Authorization may not proceed unless
the generated and published build receipts compare byte for byte. Use
[private input construction](private-input-construction.md) only for the
corresponding validation, canonical-byte construction, and exclusive file
creation procedures.

The future fixture's identifiers are recorded only after their approved
creation and verification; they must never be guessed. If task or path creation
is uncertain, record only known identity fields and retain the possible
resource pending an operational decision.

Create the cleanup manifest after the distinct package-cleanup phase ends when
restoration is verified. When restoration was not required, create it without
deleting package paths. When restoration is incomplete or unverified, create
it as the retained recovery record without deleting anything. Its intended
private path and the separate Linux-observation path are bound before the run.
Private cleanup remains deferred to issue 281.

The executor must first verify the actual positive grant against the published
source revision. Resolve missing fields before the corresponding action. Any
changed fixture, artifact, access scope, launcher, argument file, protected
asset, package identity, or cleanup target returns for a decision.

The source experiment excludes malicious code running as the same user. Hashes,
nonces, stable descriptors, and file identities narrow substitution and
freshness risks; they do not authenticate the producer or make launch atomic.
Uncancellable or synchronously blocking getters, package changes during the
probe, managed task-deletion cascades, and restoration of task state remain
concrete operating risks. The no-send probe cannot qualify notification
delivery or acknowledgment.
