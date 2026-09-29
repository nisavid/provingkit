# Application staging and restoration

This runbook implements [Prepare and review the disposable observer probe](https://github.com/nisavid/provingkit/issues/278) as one operator-run window: create one fixture, protect the installed archive, atomically exchange in the reviewed candidate, run one bounded observer arm, stop it, restore the pristine archive, and verify restored behavior.
LIVE operation requires later authorization.

## Approval boundary

[Authorize the disposable Desktop observer probe](https://github.com/nisavid/provingkit/issues/279) must bind every variable to one exact value and every path variable to one exact absolute path. The packet must not use `eval`, `source`, untrusted shell expansion, or paths copied from this committed document:

- `RUN_ID`, beginning with `278-`.
- `PROBE_INSTALL_ROOT`, derived from package ownership.
- `CANDIDATE_ARCHIVE` and `GENERATED_BUILD_RECEIPT`, naming the same build output directory's `candidate.asar` and `build-receipt.json`.
- `PUBLISHED_BUILD_RECEIPT`, naming the reviewed revision's retained `candidate-build.json`.
- `CANDIDATE_SHA256` and the reviewed archive-verification record.
- `PROBE_SYSTEM_STATE_ROOT`, a root-owned `0700` directory prepared only under the later authorization.
- `PROBE_USER_STATE_ROOT`, the existing private output root.
- `PROBE_CONFIG`, a private regular file outside the empty run directory.
- `CLEANUP_MANIFEST`, a private path outside the run directory that does not exist before the run.
- `PROBE_LAUNCHER`, its SHA-256 as `PROBE_LAUNCHER_SHA256`, and its reviewed device, inode, owner, group, mode, link count, and size as `PROBE_LAUNCHER_STAT`.
- The reviewed NUL-delimited `PROBE_LAUNCH_ARGV_FILE`, its reconstructed NUL-delimited SHA-256 as `PROBE_LAUNCH_ARGV_SHA256`, and its device, inode, owner, group, mode, link count, and size as `PROBE_LAUNCH_ARGV_STAT`.
- `PROTECTED_ASSET_MANIFEST`, its SHA-256, and the exact main-executable, complete native-asset, and `chrome-sandbox` inventory.
- The current profile, account, organization, new local Code task, dedicated empty worktree and project, task ID, Code ID, metadata path, approved process bindings, and task-restoration expectations.

Any required root preparation is part of the later authorization packet, not a
requirement already completed by this document. If a required root does not
exist at preflight, stop for its separately authorized root-creation step; do
not create a directory chain through unchecked ancestors.

The packet must confirm:

- Package `claude-desktop-extra 2.9939.4-1`.
- Application archive `@ant/desktop 2.9939.4`.
- Electron `44.4.3`.
- Installed target `PROBE_INSTALL_ROOT/resources/app.asar`.
- Pristine SHA-256 `4ac2b896dabf3e871f9cf6d9833d02f9f6ad2a839dae6658edc84bb08341238a`.
- Target: regular `root:root` file, mode `0644`, one link, `54910454` bytes, base ACL only, and no xattrs.
- Resources directory: `root:root`, mode `0755`.
- Main executable: `root:root`, mode `0755`.
- `chrome-sandbox`: `root:root`, mode `4755`.
- The launcher and every ancestor are root-owned and not group- or world-writable.
- The launcher ignores `CLAUDE_APP_ASAR`, loads the executable-adjacent archive, and creates the profile binary with symlinks to shared resources.

`build-receipt.json` is generated output tied to the proposed archive.
`candidate-build.json` is its published source copy. Both bind source-input
hashes and the candidate archive hash, but neither contains the published Git
revision; approval must bind and review that revision separately. Authorization
and staging require the two receipt files to compare byte for byte. Host
metadata proves installed ownership. UID `65534` observed in the sandbox
namespace does not.

## Fixture preparation

Before closing Claude Desktop or staging files, use the current signed-in
profile and a new dedicated empty worktree and project to create exactly one new
local Code task. Send the exact first prompt:

```text
This is a disposable observer fixture. Reply exactly `PROBE_READY`. Do not use tools, inspect files, change settings, or begin other work.
```

Select only that task's metadata. Record its task ID, Code ID, metadata path,
profile, account, organization, local backend, project, and worktree in the
private packet. Confirm that it has no parent task, child task, shared task,
shared project, shared worktree, or other link that deletion could follow.
Missing or changing IDs, a non-local backend, a metadata mismatch, or any shared
or linked state is a stop condition; do not create another fixture or rescope.

Prepare `PROBE_CONFIG` before staging. It must carry the existing schema, exact
fixture and artifact binding, private run directory, and setup limits described
by `probe-procedure.md`. Do not acquire private identity data before the later
grant.

Record the fixture's expected post-restoration state in the approval packet.
The cleanup manifest is created only after restoration verification, when every
emitted file and final retained identity can be inventoried exactly.

## Preflight

Coordinate the one current-profile window so no package operation is active or
scheduled to overlap it. Do not change global updater configuration.

```bash
set -euo pipefail
export LC_ALL=C

required=(RUN_ID PROBE_INSTALL_ROOT CANDIDATE_ARCHIVE
  GENERATED_BUILD_RECEIPT PUBLISHED_BUILD_RECEIPT CANDIDATE_SHA256
  REVIEWED_ARCHIVE_VERIFICATION PROBE_SYSTEM_STATE_ROOT
  PROBE_USER_STATE_ROOT PROBE_CONFIG CLEANUP_MANIFEST
  PROBE_LAUNCHER PROBE_LAUNCHER_SHA256 PROBE_LAUNCHER_STAT
  PROBE_LAUNCH_ARGV_FILE PROBE_LAUNCH_ARGV_SHA256 PROBE_LAUNCH_ARGV_STAT
  PROTECTED_ASSET_MANIFEST PROTECTED_ASSET_MANIFEST_SHA256)
for name in "${required[@]}"; do
  [[ -n "${!name:-}" ]]
done
[[ "$RUN_ID" =~ ^278-[A-Za-z0-9._-]+$ ]]

TARGET_DIR="$PROBE_INSTALL_ROOT/resources"
TARGET="$TARGET_DIR/app.asar"
STAGE="$TARGET_DIR/.app.asar.probe-$RUN_ID.exchange"
BACKUP_RUN_ROOT="$PROBE_SYSTEM_STATE_ROOT/$RUN_ID"
BACKUP="$BACKUP_RUN_ROOT/pristine-app.asar"
OUTPUT_RUN_ROOT="$PROBE_USER_STATE_ROOT/$RUN_ID"
PRISTINE_SHA256="4ac2b896dabf3e871f9cf6d9833d02f9f6ad2a839dae6658edc84bb08341238a"

test "${CANDIDATE_ARCHIVE##*/}" = "candidate.asar"
test "${GENERATED_BUILD_RECEIPT##*/}" = "build-receipt.json"
test "${PUBLISHED_BUILD_RECEIPT##*/}" = "candidate-build.json"
test "${CANDIDATE_ARCHIVE%/*}" = "${GENERATED_BUILD_RECEIPT%/*}"

for path in "$PROBE_INSTALL_ROOT" "$CANDIDATE_ARCHIVE" \
  "$GENERATED_BUILD_RECEIPT" "$PUBLISHED_BUILD_RECEIPT" \
  "$REVIEWED_ARCHIVE_VERIFICATION" "$PROBE_SYSTEM_STATE_ROOT" \
  "$PROBE_USER_STATE_ROOT" "$PROBE_CONFIG" "$CLEANUP_MANIFEST" \
  "$PROBE_LAUNCHER" "$PROBE_LAUNCH_ARGV_FILE" \
  "$PROTECTED_ASSET_MANIFEST"; do
  [[ "$path" = /* && "$path" != *$'\n'* && "$path" != *'/../'* ]]
  cursor="/"
  IFS=/ read -r -a components <<< "${path#/}" || exit 1
  for component in "${components[@]}"; do
    [[ -n "$component" && "$component" != "." && "$component" != ".." ]]
    cursor="${cursor%/}/$component"
    sudo test ! -L "$cursor"
  done
done

check_root_owned_directory() {
  local path="$1" owner mode
  sudo test -d "$path"
  owner=$(sudo stat -c '%u' -- "$path") || return 1
  mode=$(sudo stat -c '%a' -- "$path") || return 1
  test "$owner" = "0"
  (( (8#$mode & 0022) == 0 ))
}

check_root_owned_ancestors() {
  local path="$1" cursor="/" component
  local -a components
  check_root_owned_directory "/"
  IFS=/ read -r -a components <<< "${path#/}" || return 1
  for component in "${components[@]}"; do
    [[ -n "$component" && "$component" != "." && "$component" != ".." ]]
    cursor="${cursor%/}/$component"
    check_root_owned_directory "$cursor"
  done
}

check_root_owned_parent_ancestors() {
  local path="$1" parent
  parent="${path%/*}"
  [[ -n "$parent" ]] || parent="/"
  check_root_owned_ancestors "$parent"
}

check_root_owned_ancestors "$PROBE_INSTALL_ROOT"
check_root_owned_ancestors "$PROBE_SYSTEM_STATE_ROOT"
check_root_owned_parent_ancestors "$PROBE_LAUNCHER"

sudo test -d "$PROBE_SYSTEM_STATE_ROOT"
test "$(sudo stat -c '%u:%g:%a' -- "$PROBE_SYSTEM_STATE_ROOT")" = "0:0:700"
test -d "$PROBE_USER_STATE_ROOT"
test -f "$PROBE_CONFIG"
test ! -L "$PROBE_CONFIG"
test "$(stat -c '%a:%h' -- "$PROBE_CONFIG")" = "600:1"
[[ "$PROBE_CONFIG" != "$OUTPUT_RUN_ROOT"/* ]]
[[ "$CLEANUP_MANIFEST" != "$OUTPUT_RUN_ROOT"/* ]]
test ! -e "$CLEANUP_MANIFEST"
test ! -L "$CLEANUP_MANIFEST"

package_line=$(pacman -Q -- claude-desktop-extra) || exit 1
test "$package_line" = "claude-desktop-extra 2.9939.4-1"
owner_line=$(pacman -Qo -- "$TARGET") || exit 1
test "$owner_line" = \
  "$TARGET is owned by claude-desktop-extra 2.9939.4-1"

hash_file() {
  local output digest marker extra
  output=$(sudo sha256sum -- "$1") || return 1
  read -r digest marker extra <<< "$output" || return 1
  test "$marker" = "$1"
  test -z "${extra:-}"
  printf '%s' "$digest"
}

check_no_xattrs() {
  local output
  output=$(sudo getfattr --absolute-names -d -m- -- "$1") || return 1
  test -z "$output"
}

check_reviewed_launcher() {
  local actual mode
  check_root_owned_parent_ancestors "$PROBE_LAUNCHER"
  sudo test -f "$PROBE_LAUNCHER"
  sudo test ! -L "$PROBE_LAUNCHER"
  actual=$(sudo stat -c '%d:%i:%u:%g:%a:%h:%s' -- "$PROBE_LAUNCHER") ||
    return 1
  test "$actual" = "$PROBE_LAUNCHER_STAT"
  test "$(sudo stat -c '%u' -- "$PROBE_LAUNCHER")" = "0"
  mode=$(sudo stat -c '%a' -- "$PROBE_LAUNCHER") || return 1
  (( (8#$mode & 0022) == 0 ))
  test "$(hash_file "$PROBE_LAUNCHER")" = "$PROBE_LAUNCHER_SHA256"
}

load_reviewed_launch_argv() {
  local destination_name="$1" argv_fd path_before descriptor_before
  local descriptor_after path_after item hash_output digest marker extra
  local -n destination="$destination_name"

  destination=()
  test -f "$PROBE_LAUNCH_ARGV_FILE"
  test ! -L "$PROBE_LAUNCH_ARGV_FILE"
  path_before=$(stat -c '%d:%i:%u:%g:%a:%h:%s' -- \
    "$PROBE_LAUNCH_ARGV_FILE") || return 1
  test "$path_before" = "$PROBE_LAUNCH_ARGV_STAT"

  exec {argv_fd}<"$PROBE_LAUNCH_ARGV_FILE" || return 1
  descriptor_before=$(stat -Lc '%d:%i:%u:%g:%a:%h:%s' -- \
    "/proc/self/fd/$argv_fd") || {
      exec {argv_fd}<&-
      return 1
    }
  test "$descriptor_before" = "$path_before" || {
    exec {argv_fd}<&-
    return 1
  }

  while true; do
    item=
    if IFS= read -r -d '' item <&"$argv_fd"; then
      destination+=("$item")
      continue
    fi
    test -z "$item" || {
      exec {argv_fd}<&-
      return 1
    }
    break
  done

  descriptor_after=$(stat -Lc '%d:%i:%u:%g:%a:%h:%s' -- \
    "/proc/self/fd/$argv_fd") || {
      exec {argv_fd}<&-
      return 1
    }
  path_after=$(stat -c '%d:%i:%u:%g:%a:%h:%s' -- \
    "$PROBE_LAUNCH_ARGV_FILE") || {
      exec {argv_fd}<&-
      return 1
    }
  exec {argv_fd}<&-

  test ! -L "$PROBE_LAUNCH_ARGV_FILE"
  test "$descriptor_after" = "$descriptor_before"
  test "$path_after" = "$path_before"
  test "${#destination[@]}" -gt 0
  test "${destination[0]}" = "$PROBE_LAUNCHER"

  hash_output=$(printf '%s\0' "${destination[@]}" | sha256sum) || return 1
  read -r digest marker extra <<< "$hash_output" || return 1
  test "$marker" = "-"
  test -z "${extra:-}"
  test "$digest" = "$PROBE_LAUNCH_ARGV_SHA256"
}

test -d "$TARGET_DIR"
test "$(stat -c '%u:%g:%a' -- "$TARGET_DIR")" = "0:0:755"
test -f "$TARGET"
test ! -L "$TARGET"
test "$(stat -c '%u:%g:%a:%h:%s' -- "$TARGET")" = \
  "0:0:644:1:54910454"
test "$(hash_file "$TARGET")" = "$PRISTINE_SHA256"
target_acl=$(getfacl -cp -- "$TARGET") || exit 1
test "$target_acl" = $'user::rw-\ngroup::r--\nother::r--'
check_no_xattrs "$TARGET"

for file in "$CANDIDATE_ARCHIVE" "$GENERATED_BUILD_RECEIPT" \
  "$PUBLISHED_BUILD_RECEIPT" "$REVIEWED_ARCHIVE_VERIFICATION" \
  "$PROBE_LAUNCH_ARGV_FILE" "$PROTECTED_ASSET_MANIFEST"; do
  test -f "$file"
  test ! -L "$file"
  test "$(stat -c '%h' -- "$file")" = "1"
done

cmp -s -- "$GENERATED_BUILD_RECEIPT" "$PUBLISHED_BUILD_RECEIPT"
test "$(hash_file "$CANDIDATE_ARCHIVE")" = "$CANDIDATE_SHA256"
test "$(hash_file "$PROTECTED_ASSET_MANIFEST")" = \
  "$PROTECTED_ASSET_MANIFEST_SHA256"
check_reviewed_launcher
PREFLIGHT_LAUNCH_ARGV=()
load_reviewed_launch_argv PREFLIGHT_LAUNCH_ARGV
unset PREFLIGHT_LAUNCH_ARGV

sudo test ! -e "$STAGE"
sudo test ! -L "$STAGE"
sudo test ! -e "$BACKUP_RUN_ROOT"
sudo test ! -L "$BACKUP_RUN_ROOT"
test ! -e "$OUTPUT_RUN_ROOT"
test ! -L "$OUTPUT_RUN_ROOT"
mv --help | grep -q -- '--exchange'
mv --help | grep -q -- '--no-copy'
```

Review the generated and published receipts, their byte-for-byte comparison, the
separately bound published revision, and the archive-verification record.
Confirm that the candidate hash comes from that receipt and that the complete
unchanged-asset inventory matches it.

Verify every protected-asset manifest row by reading its fixed tab-delimited
fields as data, checking that its absolute path is under `PROBE_INSTALL_ROOT`,
and comparing SHA-256, owner, group, mode, link count, and size with
`sha256sum` and `stat`. Require exactly one reviewed main executable, every
reviewed native asset, and exactly one `chrome-sandbox`. Do not execute or
evaluate manifest content. Save this verified manifest for restoration.

Quit Claude Desktop through its UI. Under the later grant, the exact selected
application PID may be checked against the profile-specific `SingletonLock`;
static review only establishes that the lock contains a PID. Do not infer that
one PID proves every process has exited. If the current profile is not
quiescent, stop. If another Desktop instance uses the shared installed
resources, return for an operating decision. Do not enumerate unrestricted
processes.

```bash
install -d -m 0700 -- "$OUTPUT_RUN_ROOT"
sudo install -d -o 0 -g 0 -m 0700 -- "$BACKUP_RUN_ROOT"
sudo cp --preserve=all --reflink=never -- "$TARGET" "$BACKUP"

sudo test -f "$BACKUP"
sudo test ! -L "$BACKUP"
test "$(sudo stat -c '%u:%g:%a:%h:%s' -- "$BACKUP")" = \
  "0:0:644:1:54910454"
test "$(hash_file "$BACKUP")" = "$PRISTINE_SHA256"
backup_acl=$(sudo getfacl -cp -- "$BACKUP") || exit 1
test "$backup_acl" = $'user::rw-\ngroup::r--\nother::r--'
check_no_xattrs "$BACKUP"
sudo cmp -s -- "$TARGET" "$BACKUP"
```

## Atomic candidate exchange

The build receipts must still compare byte for byte immediately before the
candidate is copied into the package-owned staging path.

```bash
cmp -s -- "$GENERATED_BUILD_RECEIPT" "$PUBLISHED_BUILD_RECEIPT"
test "$(hash_file "$CANDIDATE_ARCHIVE")" = "$CANDIDATE_SHA256"

sudo install -o 0 -g 0 -m 0644 -- "$CANDIDATE_ARCHIVE" "$STAGE"
sudo test -f "$STAGE"
sudo test ! -L "$STAGE"
test "$(sudo stat -c '%u:%g:%a:%h' -- "$STAGE")" = "0:0:644:1"
test "$(hash_file "$STAGE")" = "$CANDIDATE_SHA256"
stage_acl=$(sudo getfacl -cp -- "$STAGE") || exit 1
test "$stage_acl" = $'user::rw-\ngroup::r--\nother::r--'
check_no_xattrs "$STAGE"
sudo sync -f -- "$STAGE"
```

Immediately repeat the package, ownership, target identity, pristine hash, ACL,
xattr, backup, receipt comparison, and protected-asset manifest checks. Then
exchange:

```bash
sudo mv --exchange --no-copy -- "$STAGE" "$TARGET"
sudo sync -f -- "$TARGET_DIR"
test "$(hash_file "$TARGET")" = "$CANDIDATE_SHA256"
test "$(sudo stat -c '%u:%g:%a:%h' -- "$TARGET")" = "0:0:644:1"
test "$(hash_file "$STAGE")" = "$PRISTINE_SHA256"
test "$(sudo stat -c '%u:%g:%a:%h:%s' -- "$STAGE")" = \
  "0:0:644:1:54910454"
sudo cmp -s -- "$STAGE" "$BACKUP"
```

Unknown identities are a stop condition. If the pristine stage is lost, retain
the protected backup and stop; do not use an unreviewed fallback.

## Launch and collection

Immediately before the candidate launch, repeat `pacman -Q`, `pacman -Qo`, the
target candidate identity, the complete protected-asset manifest, and the
receipt comparison. Revalidate the root-owned launcher and its ancestors, then
read the argument file once through one stable descriptor. Use only the
validated in-memory array produced from that descriptor.

```bash
package_line=$(pacman -Q -- claude-desktop-extra) || exit 1
test "$package_line" = "claude-desktop-extra 2.9939.4-1"
owner_line=$(pacman -Qo -- "$TARGET") || exit 1
test "$owner_line" = \
  "$TARGET is owned by claude-desktop-extra 2.9939.4-1"
test "$(hash_file "$TARGET")" = "$CANDIDATE_SHA256"
cmp -s -- "$GENERATED_BUILD_RECEIPT" "$PUBLISHED_BUILD_RECEIPT"

PROBE_LAUNCH_ARGV=()
load_reviewed_launch_argv PROBE_LAUNCH_ARGV
check_reviewed_launcher
env PROVINGKIT_OBSERVER_CONFIG="$PROBE_CONFIG" "${PROBE_LAUNCH_ARGV[@]}"
```

The launcher check and stable argument-file read narrow the mutation window;
they do not make script execution atomic. A changed package, launcher, launcher
ancestor, argument-file identity, reconstructed argument digest, or protected
asset is a stop condition. Preserve every original argument exactly.

After candidate launch and before waiting for bootstrap, submit this exact
second prompt on the same recorded fixture:

```text
This is a disposable observer fixture. Reply exactly `PROBE_READY`. Do not use tools, inspect files, change settings, or begin other work.
```

The sidecar writes `bootstrap.json` into the selected private run directory
after binding the existing query. Under the later grant, the executor reads only
that exact file, compares every binding field with the approved task, Code
identity, and candidate bytes, then writes the matching `arm.json`. The three
query getters run only after arm acceptance. Collect for at most 30 seconds.

The reviewed helper is limited to the selected reported PID, three bounded
`stat` reads, two executable opens, and 256 MiB of hashing. It must not read
environments, command lines, unrelated processes, transcripts, or historical
peers. Comparing a process report does not establish the Code query's
OS-process association; that remains unknown.

This window permits one arm only. A timeout or failed experiment requires a new
plan and window, not an automatic retry.

After collection ends, whether successfully or unsuccessfully, quit Claude
Desktop through its UI before any restoration check or exchange. Verify that
the exact selected PID has exited where that can be established, then verify
that the current profile is quiescent. One observed PID does not prove that all
activity has ended. If the profile is not quiescent or an unknown or shared
consumer still uses the installed resources, stop for an operating decision.

## Restore and verify

Before reversing, repeat `pacman -Q`, `pacman -Qo`, the complete protected-asset
manifest, and these identity checks:

```bash
test "$(hash_file "$TARGET")" = "$CANDIDATE_SHA256"
test "$(sudo stat -c '%u:%g:%a:%h' -- "$TARGET")" = "0:0:644:1"
test "$(hash_file "$STAGE")" = "$PRISTINE_SHA256"
test "$(sudo stat -c '%u:%g:%a:%h:%s' -- "$STAGE")" = \
  "0:0:644:1:54910454"
test "$(hash_file "$BACKUP")" = "$PRISTINE_SHA256"
sudo cmp -s -- "$STAGE" "$BACKUP"
```

If the package version changed, ownership is unknown, or either archive
identity fails, do not reverse the exchange.

```bash
sudo mv --exchange --no-copy -- "$STAGE" "$TARGET"
sudo sync -f -- "$TARGET_DIR"

test "$(hash_file "$TARGET")" = "$PRISTINE_SHA256"
test "$(sudo stat -c '%u:%g:%a:%h:%s' -- "$TARGET")" = \
  "0:0:644:1:54910454"
restored_acl=$(sudo getfacl -cp -- "$TARGET") || exit 1
test "$restored_acl" = $'user::rw-\ngroup::r--\nother::r--'
check_no_xattrs "$TARGET"
sudo cmp -s -- "$TARGET" "$BACKUP"
test "$(hash_file "$STAGE")" = "$CANDIDATE_SHA256"
```

Repeat package, ownership, complete manifest, and reviewed archive-verification
checks. Immediately before the restored launch, recheck the package and
pristine target, revalidate the launcher and its root-owned ancestors, and
reconstruct the argument array through a newly opened stable descriptor. Do not
reuse the candidate launch's array or reopen the argument path after validation.

```bash
package_line=$(pacman -Q -- claude-desktop-extra) || exit 1
test "$package_line" = "claude-desktop-extra 2.9939.4-1"
owner_line=$(pacman -Qo -- "$TARGET") || exit 1
test "$owner_line" = \
  "$TARGET is owned by claude-desktop-extra 2.9939.4-1"
test "$(hash_file "$TARGET")" = "$PRISTINE_SHA256"

PROBE_LAUNCH_ARGV=()
load_reviewed_launch_argv PROBE_LAUNCH_ARGV
check_reviewed_launcher
env -u PROVINGKIT_OBSERVER_CONFIG "${PROBE_LAUNCH_ARGV[@]}"
```

Verify the selected profile opens and inspect the same fixture against the
recorded restoration expectations. Restored bytes, protected assets, and task
behavior are separate acceptance checks.

## Package cleanup

Immediately before deleting the package staging copy and protected backup,
repeat the exact `STAGE` candidate identity and `BACKUP` pristine identity,
metadata, ACL, xattr, and comparison checks.

```bash
test "$(hash_file "$STAGE")" = "$CANDIDATE_SHA256"
test "$(sudo stat -c '%u:%g:%a:%h' -- "$STAGE")" = "0:0:644:1"
test "$(hash_file "$BACKUP")" = "$PRISTINE_SHA256"
test "$(sudo stat -c '%u:%g:%a:%h:%s' -- "$BACKUP")" = \
  "0:0:644:1:54910454"
sudo cmp -s -- "$TARGET" "$BACKUP"

sudo rm -- "$STAGE"
sudo rm -- "$BACKUP"
sudo rmdir -- "$BACKUP_RUN_ROOT"
```

Retain mismatched artifacts and stop. Remove no other package-owned path.

## Private cleanup manifest and retention

Raw output remains private through [Decide what the observer probe establishes](https://github.com/nisavid/provingkit/issues/281).
After restored behavior has been checked, but before returning the run for that
decision, create `CLEANUP_MANIFEST` as a private regular, single-link `0600`
file. It is an inventory, not an executable cleanup script. Its schema is:

```json
{
  "schema": "provingkit.desktop-probe-cleanup.v1",
  "createdAt": "RFC-3339 timestamp",
  "runId": "exact RUN_ID",
  "source": {
    "publishedRevision": "exact reviewed Git revision"
  },
  "artifacts": {
    "candidateSha256": "receipt value",
    "managerSha256": "receipt value",
    "sidecarSha256": "receipt value",
    "generatedBuildReceiptSha256": "SHA-256 of build-receipt.json",
    "publishedBuildReceiptSha256": "same SHA-256",
    "archiveVerificationSha256": "SHA-256 of the reviewed verification record"
  },
  "fixture": {
    "profile": "exact selected profile identity",
    "accountId": "exact selected account identity",
    "organizationId": "exact selected organization identity or explicit null",
    "backend": "local",
    "taskId": "exact disposable task identity",
    "codeId": "exact Code session identity",
    "metadataPath": "exact absolute selected metadata path",
    "project": {
      "path": "exact absolute dedicated project path",
      "device": "decimal device",
      "inode": "decimal inode",
      "uid": "decimal owner",
      "gid": "decimal group",
      "mode": "octal mode",
      "dedicated": true,
      "emptyAtFixtureCreation": true
    },
    "worktree": {
      "path": "exact absolute dedicated worktree path",
      "device": "decimal device",
      "inode": "decimal inode",
      "uid": "decimal owner",
      "gid": "decimal group",
      "mode": "octal mode",
      "dedicated": true,
      "emptyAtFixtureCreation": true
    },
    "links": {
      "parentTaskId": null,
      "childTaskIds": [],
      "sharedTaskIds": [],
      "sharedProject": false,
      "sharedWorktree": false,
      "validatedAt": "RFC-3339 timestamp"
    }
  },
  "configuration": {
    "path": "exact absolute PROBE_CONFIG",
    "type": "regular-file",
    "device": "decimal device",
    "inode": "decimal inode",
    "uid": "decimal owner",
    "gid": "decimal group",
    "mode": "0600",
    "links": 1,
    "size": "decimal bytes",
    "sha256": "lowercase SHA-256"
  },
  "output": {
    "root": {
      "path": "exact absolute OUTPUT_RUN_ROOT",
      "type": "directory",
      "device": "decimal device",
      "inode": "decimal inode",
      "uid": "decimal owner",
      "gid": "decimal group",
      "mode": "0700"
    },
    "emittedFiles": [
      {
        "role": "bootstrap, arm, or one exact numbered sample",
        "path": "exact absolute direct child of OUTPUT_RUN_ROOT",
        "type": "regular-file",
        "device": "decimal device",
        "inode": "decimal inode",
        "uid": "decimal owner",
        "gid": "decimal group",
        "mode": "0600",
        "links": 1,
        "size": "decimal bytes",
        "sha256": "lowercase SHA-256"
      }
    ]
  }
}
```

List every file actually emitted, including `arm.json`; do not list a pattern,
range, glob, or file that does not exist. Every emitted path must be a direct
child of the exact output root. The manifest must bind the same source,
artifact, task, Code, profile, project, worktree, configuration, and output
identities already accepted for the run. A mismatch leaves all private data
retained.

Issue 281 may approve deletion only by naming the reviewed cleanup manifest and
its SHA-256, the exact task identity, and the exact manifest roles or paths to
remove. Anything not named remains retained. Approval to retain a redacted
summary does not imply approval to remove raw evidence.

Source inspection found that `LocalSessions.delete(sessionId)` delegates to
`manager.deleteSession` with `userInitiated: true`, and manager teardown may
cascade to linked tasks, associated worktrees, and transcripts. Do not call
either internal method, invoke a private API, or add cleanup instrumentation.
Before deletion, revalidate that the task and Code IDs match the manifest, the
task has no parent, child, or shared links, and its project and worktree are
dedicated to this fixture.

Use only Desktop's normal task-deletion UI. Proceed only when the live UI shows
the selected disposable fixture and its confirmation scope matches that exact
task. UI labels and controls are not assumed by this runbook. If the control is
absent, the selected identity cannot be confirmed, or the confirmation
indicates broader scope, retain the exact artifact and return for an operational
decision. The approved cleanup accepts managed removal of that task's own
transcript and dedicated worktree. If any broader side effect is shown or
observed, stop without continuing file cleanup and report it.

After the exact UI deletion, confirm that the selected task is absent and that
no known unrelated task, worktree, project, or transcript changed. Do not
manually delete Desktop private profile stores, task metadata, transcripts,
other worktrees, or any application-managed residual path.

Remove an approved user-owned configuration or output file only with this
manual checklist:

1. Copy its exact path and expected type, device, inode, UID, GID, mode, link
   count, size, and SHA-256 from the reviewed manifest into the executor's
   checklist as literal data. Do not evaluate the manifest as shell.
2. Require an absolute path without a newline, `.` or `..` component, and
   verify every existing component is not a symlink.
3. For an output file, require the exact output-root prefix and a nonempty
   remainder containing no slash, so the file is a direct child. For the
   configuration, require exact equality with the manifest's configuration
   path and require that it is outside the output root.
4. Compare `lstat`, owner, group, mode, link count, size, and SHA-256 with the
   manifest. Require a regular file and one link. A mismatch retains the file.
5. Run `unlink -- "$EXACT_APPROVED_PATH"` for that one path. Verify both
   `test ! -e "$EXACT_APPROVED_PATH"` and
   `test ! -L "$EXACT_APPROVED_PATH"` afterward.

Process approved output files one at a time in manifest order. Do not use a
glob, brace expansion, recursive removal, or inferred numbered range. After the
approved files are removed, compare the output root's device, inode, owner,
group, and mode with the manifest. Check exact emptiness with a bounded
one-level listing whose failure is handled. Use `rmdir -- "$OUTPUT_RUN_ROOT"`
only when it is empty, then verify the exact path is absent. An unexpected or
unapproved entry remains in place and returns for a decision.

If the exact manifest-listed project or worktree directory remains after the UI
operation, compare its device, inode, owner, group, and mode with the manifest,
confirm it is still dedicated to the deleted fixture, and verify it is empty.
Only then may `rmdir -- "$EXACT_DIRECTORY"` remove that one directory. Do not
unlink directory contents to make it empty. A missing directory is an accepted
managed effect; a nonempty, changed, shared, or differently owned directory is
retained.

The cleanup manifest itself remains private decision evidence unless issue 281
separately binds its exact path, external hash and file identity, and approves
unlinking it last. No glob, broad recursive removal, permanent instrumentation,
maintained observer deployment, periodic commitment, or expanded qualification
is authorized.
