# Authorize one disposable observer probe

Use this checklist in the authorization ticket after independent review of the
candidate. Record accepted or amended terms in the user's own decision. A
source review or completed preparation ticket supplies no live grant.

| Scope | Terms to confirm |
| --- | --- |
| Source and application bytes | Published procedure/source revision; generated `build-receipt.json` tied to the proposed archive; published `candidate-build.json`; mandatory byte-for-byte comparison between them; exact archive, manager, and sidecar digests from that receipt; complete archive-verification record |
| App changes | Temporary replacement of the inspected installed archive, preserving executable, native assets, launcher, and sandbox layout; close before staging, close before restoration, and launch after each exchange |
| Operating window | One scheduled window using the current signed-in profile; two full shutdown/launch cycles, two exact setup prompts, and the listed manual preflight and restoration checks; getter initiation, asynchronous waiting, and settlement acceptance use one 30-second monotonic observation deadline, without a hard-cancellation or total-duration claim; total duration remains an unmeasured scheduling unknown |
| Launcher | Exact launcher path, SHA-256, device, inode, owner, group, mode, link count, and size; root-owned non-writable ancestors; exact NUL-delimited argument-file path, identity, and reconstructed byte digest; stable-descriptor validation immediately before both launches |
| Fixture | One new top-level local Code task named `Desktop observer probe 278`, created through the normal new-task UI in a new dedicated empty non-Git directory; never fork, spawn, import, duplicate, or reuse; do not resolve or invent a worktree before creation; if Desktop creates one, bind its identity and exact expected app-managed entries; bind the actual profile, account, organization, task ID, Code ID, real directory identities, Electron app-data root, the concrete `claude-code-sessions` base, and the constructed metadata path before staging; never call internal `getSessionFilePath` |
| Fixture isolation | Project only `sessionId`, `cliSessionId`, `cwd`, `originCwd`, `worktreePath`, `spawnedFrom`, `dispatchParentId`, `dispatchParentOrigin`, `forkedFromSessionId`, and `lineageDetached` from the selected file; require `cwd` to match the dedicated project and record each optional path as absent, empty, or an approved nonempty real-directory identity; preserve each optional lineage field's presence, stop on a non-null relation or true `lineageDetached`, and do not convert absence into confirmed nonrelation; record local creation from the normal UI provenance and keep the static adapter guard for live `backend.kind === "local"` with undefined SSH and WSL configuration as separate source evidence, not persisted metadata or live proof; stop on a path, identity, directory-shape, or activity discrepancy; record global child and unrelated-sharing absence as not established |
| Setup | Two submissions of the exact `PROBE_READY` prompt in the procedure, one before staging and one afterward, on that fixture only |
| Local configuration | One exclusively created private configuration outside a new private run directory; deterministic canonical UTF-8 bytes with no BOM or final newline; exact selected paths, task and Code IDs, receipt candidate and module hashes, 60-second setup deadline, and 100-millisecond setup polling |
| Arm and getters | Validate the selected bootstrap before arm; record every generated binding value; exclusively create one canonical UTF-8 arm that echoes every `BINDING_KEYS` field, including `monotonicClockId` and `linuxBootId`; accept it within 60 seconds of bootstrap; three sample initiations at least five seconds apart; getter initiation, asynchronous waiting, and settlement acceptance bounded by one 30-second monotonic observation window; the three named getters sequentially with waits of at most two seconds each and clamped to the remaining window; no hard cancellation claim for uncancellable or synchronously blocking work; no retry after terminal failure |
| Receiver data | The procedure's named provider/model, rules/directory grants, account IDs, host settings/grants, cwd, and Code process/version report; no prompt/transcript, credential, environment, or raw-error export |
| Linux process observation | One separately invoked observation sourced from a freshly validated sample with matching before/after reports; one read of the single nonsecret Linux boot-ID path `/proc/sys/kernel/random/boot_id` for each of the initial and final sample acquisitions; bind monotonic timestamps to `linux-clock-monotonic.v1` and that boot ID; pass explicit fresh wall and monotonic clock values to direct `readProbeSample` or `inspectProbeSample` calls; two selected-PID path metadata checks and one owned `O_DIRECTORY | O_NOFOLLOW` descriptor open; seven descriptor metadata checks, including owner, identity, and fresh wall and monotonic limits immediately before each child open; child resolution only through the retained descriptor; three `stat` opens reading at most 4,096 bytes each; two opens of `exe`; at most 256 MiB hashed; no PID-path child re-resolution, enumeration, or alternate PID |
| State changes | No deliberate account, model, permission, grant, or cwd transitions; stop for a separately reviewed proposal if one becomes necessary |
| Retained Linux result | Validate the one helper return against a documented success or explicit unknown shape, construct and canonicalize the required wrapper object, and serialize it to the bound private `selected-linux-executor-observation.json` outside the sampler directory; no implemented serializer supplies these checks; bind source, run, selected sample, and complete expected binding; reject raw errors and arbitrary objects; maximum 16384 bytes; record exact identity and digest |
| Retention | Keep raw fixture outputs, the retained Linux-observation file, and the private cleanup manifest through the return decision, accessible only to the user and authorized execution/decision workflow; remove only the exact subset that decision approves |
| Cleanup inventory | Create the private manifest after restoration verification and before return; bind source/artifact/run identities, task and Code IDs, profile route, creation provenance, selected metadata projection and evidentiary limits, the dedicated project identity, the exact absent-or-present worktree state, exact configuration, output root, every emitted file, and the separate Linux-observation artifact with type, identity, ownership, mode, size, and digest |
| Task cleanup | Revalidate the selected metadata and current coordination, then use only the normal exact-task Desktop UI; require its confirmation to establish the managed scope, including linked-task and worktree effects, as matching the fixture; accept managed removal of that task's transcript and dedicated worktree; do not call internal deletion or family APIs or scan all tasks; retain the fixture if the control or scope cannot be established |
| File cleanup | Unlink only individually approved manifest-listed user-owned files after exact identity and containment checks; use `rmdir` only for verified empty owned directories; no globs, recursive removal, manual private-store or transcript deletion, or unrelated-worktree changes |
| Restoration | Restore verified pristine package bytes, recheck protected assets, launch without the observer binding, and check application and recorded work expectations separately |

Bind the concrete paths, package metadata, receipt identities, launch arguments,
staging, cleanup-manifest path, and restoration steps from
[application staging and restoration](application-operation.md) in the private
approval packet. Authorization may not proceed unless the generated and
published build receipts compare byte for byte. Use
[private input construction](private-input-construction.md) for the complete
configuration and arm templates, selected fixture projection, and retained
Linux-result shape.

The future fixture's identifiers are recorded only after its approved creation.
They must never be guessed in advance. The cleanup manifest is created after
restoration verification, when every actual emitted file can be listed
explicitly; its intended private path and the separate Linux-observation path
are bound before the run.

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
