# Authorize one disposable observer probe

Use this checklist in the authorization ticket after independent review of the
candidate. Record accepted or amended terms in the user's own decision. A
source review or completed preparation ticket supplies no live grant.

| Scope | Terms to confirm |
| --- | --- |
| Source and application bytes | Published procedure/source revision; generated `build-receipt.json` tied to the proposed archive; published `candidate-build.json`; mandatory byte-for-byte comparison between them; exact archive, manager, and sidecar digests from that receipt; complete archive-verification record |
| App changes | Temporary replacement of the inspected installed archive, preserving executable, native assets, launcher, and sandbox layout; close before staging, close before restoration, and launch after each exchange |
| Operating window | One scheduled window using the current signed-in profile, with one candidate launch and one restored launch, explicit restoration expectations, and no unrelated shared-resource consumer |
| Launcher | Exact launcher path, SHA-256, device, inode, owner, group, mode, link count, and size; root-owned non-writable ancestors; exact NUL-delimited argument-file path, identity, and reconstructed byte digest; stable-descriptor validation immediately before both launches |
| Fixture | One disposable local Code task named `Desktop observer probe 278` in a dedicated empty project and worktree; approve creation and selected identity acquisition, then bind its actual profile/account route, metadata path, task ID, and Code ID before staging |
| Fixture isolation | No parent task, child task, shared task, shared project, shared worktree, or unrelated content that managed deletion could reach |
| Setup | Two submissions of the exact `PROBE_READY` prompt in the procedure, one before staging and one afterward, on that fixture only |
| Local configuration | One selected private configuration outside a new private run directory; exact fixture and artifact binding, 60-second setup deadline, and 100-millisecond setup polling |
| Arm and getters | One fresh exact arm, accepted within 60 seconds of bootstrap; three samples over at most 30 seconds, at least five seconds apart; the three named getters sequentially with two seconds each; no retry after terminal failure |
| Receiver data | The procedure's named provider/model, rules/directory grants, account IDs, host settings/grants, cwd, and Code process/version report; no prompt/transcript, credential, environment, or raw-error export |
| Linux process observation | One separately invoked observation sourced from a freshly validated sample with matching before/after reports; one read of the single nonsecret Linux boot-ID path `/proc/sys/kernel/random/boot_id` for each of the initial and final sample acquisitions; bind monotonic timestamps to `linux-clock-monotonic.v1` and that boot ID; pass explicit fresh wall and monotonic clock values to direct `readProbeSample` or `inspectProbeSample` calls; recheck both clocks after acquisition and after the owner check before process-file opens; selected process directory metadata, three bounded `stat` reads, two opens of `exe`, and at most 256 MiB hashed; require the calling user's UID before process-file reads, with no enumeration or alternate PID |
| State changes | No deliberate account, model, permission, grant, or cwd transitions; stop for a separately reviewed proposal if one becomes necessary |
| Retention | Keep raw fixture outputs and the private cleanup manifest through the return decision, accessible only to the user and authorized execution/decision workflow; remove only the exact subset that decision approves |
| Cleanup inventory | Create the private manifest after restoration verification and before return; bind source/artifact/run identities, task and Code IDs, profile route, dedicated project/worktree identities and link checks, exact configuration, output root, and every emitted file with type, identity, ownership, mode, size, and digest |
| Task cleanup | Use only the normal exact-task Desktop UI after live selection and confirmation scope match the fixture; accept managed removal of that task's transcript and dedicated worktree; do not call internal deletion methods; stop if the control is absent or broader effects are indicated |
| File cleanup | Unlink only individually approved manifest-listed user-owned files after exact identity and containment checks; use `rmdir` only for verified empty owned directories; no globs, recursive removal, manual private-store or transcript deletion, or unrelated-worktree changes |
| Restoration | Restore verified pristine package bytes, recheck protected assets, launch without the observer binding, and check application and recorded work expectations separately |

Bind the concrete paths, package metadata, receipt identities, launch arguments,
staging, cleanup-manifest path, and restoration steps from
[application staging and restoration](application-operation.md) in the private
approval packet. Authorization may not proceed unless the generated and
published build receipts compare byte for byte.

The future fixture's identifiers are recorded only after its approved creation.
They must never be guessed in advance. The cleanup manifest is created after
restoration verification, when every actual emitted file can be listed
explicitly; its intended private path is bound before the run.

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
