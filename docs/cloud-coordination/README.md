# Cloud coordination

This is the manual operating procedure for `chatgpt-codex-native-tree-v1`.
It uses Rolecasting and one current controller's native child tree. Source
support does not establish an installed release, published environment,
automatic startup, or qualified deployment.
Logical duties and correspondence rules are in [role-policy.md](role-policy.md).

## Start explicitly

Explicitly ask the current thread to load [BOOTSTRAP.md](BOOTSTRAP.md) from the
selected pinned distribution. It resolves the existing Rolecasting skill from
that distribution's `MANIFEST.json`. An installed catalog may still contain
older bytes: invoking its same-named skill alone does not select this runtime.
No additional public skill is required.

Start with the current thread acting as Concierge. Activate other roles only when bounded work helps the task and authority
permits it. Simple tasks can finish with one agent. If the procedure
or driver is unavailable, continue useful authorized work that needs neither;
report the missing capability when material. Do not install or download
anything as part of discovery.

## Bind and operate

Resolve every `MANIFEST.json` locator relative to the directory containing that
manifest. Load `runtime.skills.delegating_cross_agent_work` and
`runtime.skills.choosing_agent_models` from those exact files. Load
`runtime.driver.reference` and use `runtime.driver.script` from the same tree.
The driver reference owns schemas, CLI, response mappings, and recovery;
`choosing-agent-models` owns suitable supported model/effort selection. Verify
the selected file hashes and the exact bytes of `runtime.receipt.path` against
`runtime.receipt.sha256` before using the runtime. A missing or mismatched file
does not justify substituting a similarly named installed skill.

Recover the actual user grant, conditions, and holds. Preserve repository
instructions, owning worktrees, existing edits, and project responsibility.
Freeze the bounded task inputs, scope, verification, stop conditions, and
consumer assurance minimum. Review assignments retain their separate
read-only contract, denied onward authority, and independent contexts.

Inspect current native controls, then bind one local run, actor, and task-owned
SQLite store. Retain the driver/profile identity and capability observation.
Record unavailable product build explicitly; environment publication versions
are not product builds. Use observed native targets, with separate IDs only
when exposed. Directory labels and creation ancestry confer no authority.
Never publish mutable stores, payloads, handles, or obligations in an image.

For each operation, prepare and claim through the driver. Only a newly
successful claim returns the exact native call to perform once. Record the
raw response and its source, then inspect the resulting evidence. Notification
does not establish activation; previous running status does not establish a
finished interruption; timeout establishes neither failure nor nondelivery.
Keep correlation and reply intent in messages, not invented native fields.

## Verify, accept, and recover

One unresolved assignment reserves its actual child target. Preserve the
native parent, assignment owner, and reply recipient separately. A native
final returns to its parent; sibling-owned work needs an explicit correlated
reply to its owner. The owner verifies the current run, generation, assignment,
inputs, and result before explicit acceptance. Logical acceptance does not
stop a native turn: target reuse requires the driver's fresh post-closure
inventory observation.

Keep submission, receipt, completion, verification, and acceptance distinct.
Profile maxima are ceilings, not achieved evidence. Worker prose cannot prove
native identity, lifecycle, effective model, or enforced authority. Missing or
unverified results remain unusable; retain late and unknown observations.

After a lost response, preserve the uncertain claim. Inspect supported evidence
and use explicit reconciliation before another emission. A new command ID
cannot bypass unresolved work. Same-controller continuation retains verified
target/generation, suitable requested selection, and current capabilities;
foreign account routes keep their stronger requirements. A new root needs an
explicit checkpoint handoff and verified new bindings, not restoration from
an old target string. Reading a store transfers no ownership.

## Update and operating scope

The distribution contains these three support documents and a complete
`agent-plugins` runtime in `runtime/`. `MANIFEST.json` binds the full source
commit, manual startup, manifest-relative locators, the exact runtime receipt
SHA-256, and every payload file's SHA-256. It retains the runtime receipt's
canonical source repository and declares the supported operating boundary
and unqualified capabilities. Building establishes no runtime qualification,
installation, or deployment. Its inventory and `artifact_sha256`
use the release projector's `provingkit-tree-v1` framing, excluding only the
root `MANIFEST.json` itself. The runtime receipt retains its own release
projection inventory and digest. Neither receipt authenticates custody or
qualifies native behavior.

From a source checkout, create a new candidate with:

```sh
python scripts/build_cloud_coordination.py --source . --source-commit FULL_COMMIT_ID --output /private/staging/cloud-coordination
```

Replace `FULL_COMMIT_ID` with the full immutable Git commit object ID. Source
documents, policy, and runtime are read from one archived commit; dirty and
untracked checkout files are excluded. The output must be new and outside the
checkout. There is no replacement flag. Source documents without this manifest
remain development guidance, not a pinned operating entrypoint.

A distribution owner must bind reviewed identities and the actual readable
explicit locator before publication. Preserve the existing helper export.
The builder performs no installation, publication, or activation and includes
no live handles, local stores, host configuration, or account configuration.
An update verifies replacement bytes and switches the pointer;
identical selected identities are a no-op. Existing tasks retain their recorded
revision until explicitly migrated. Rollback restores the prior pinned bytes
and pointer without deleting unrelated instructions, stores, or live work.

Qualify final native operations, explicit consumer loading, update, no-op, and
rollback before claiming deployment. Automatic startup is optional follow-up
unless cheaply implemented and separately qualified. This profile claims no
account-wide directory, independent persistent chats, root wake, cross-root
restoration, portable attestation, or exactly-once native effects.
