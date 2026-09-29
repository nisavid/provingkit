# Application staging and restoration

This runbook implements [Prepare and review the disposable observer probe](https://github.com/nisavid/provingkit/issues/278) as one operator-run window: create one fixture, protect the installed archive, atomically exchange in the reviewed candidate, run one bounded observer arm, stop it, restore the pristine archive, and verify restored behavior.
LIVE operation requires later authorization.

## Approval boundary

[Authorize the disposable Desktop observer probe](https://github.com/nisavid/provingkit/issues/279) must bind every variable to one exact value and every path variable to one exact absolute path. The packet must not use `eval`, `source`, untrusted shell expansion, or paths in this committed document:

- `RUN_ID`, beginning with `278-`.
- `PROBE_INSTALL_ROOT`, derived from package ownership.
- `CANDIDATE_ARCHIVE`, `CANDIDATE_BUILD_RECEIPT`, `CANDIDATE_SHA256`, and the reviewed archive-verification record.
- `PROBE_SYSTEM_STATE_ROOT`, a root-owned `0700` directory prepared only under the later authorization.
- `PROBE_USER_STATE_ROOT`, the existing private output root.
- `PROBE_CONFIG`, a private regular file outside the empty run directory.
- `PROBE_LAUNCHER`, the reviewed NUL-delimited `PROBE_LAUNCH_ARGV_FILE`, and its SHA-256.
- `PROTECTED_ASSET_MANIFEST`, its SHA-256, and the exact main-executable, complete native-asset, and `chrome-sandbox` inventory.
- The current profile, account, organization, new local Code task, empty worktree, task ID, Code ID, metadata path, approved process bindings, and task-restoration expectations.

Any required root preparation is part of the later authorization packet, not a requirement already completed by this document. If a required root does not exist at preflight, stop for its separately authorized root-creation step; do not create a directory chain through unchecked ancestors.

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
- The launcher ignores `CLAUDE_APP_ASAR`, loads the executable-adjacent archive, and creates the profile binary with symlinks to shared resources.

`candidate-build.json` binds source-input hashes and the candidate archive hash. It does not contain the published Git revision; approval must bind and review that revision separately. Host metadata proves installed ownership. UID `65534` observed in the sandbox namespace does not.

## Fixture preparation

Before closing Claude Desktop or staging files, use the current signed-in profile and a new empty worktree to create exactly one new local Code task. Send the exact first prompt:

```text
This is a disposable observer fixture. Reply exactly `PROBE_READY`. Do not use tools, inspect files, change settings, or begin other work.
```

Select only that task’s metadata. Record its task ID, Code ID, metadata path, profile, account, organization, local backend, and empty worktree in the private packet. Missing or changing IDs, a non-local backend, or a metadata mismatch is a stop condition; do not create another fixture or rescope.

Prepare `PROBE_CONFIG` before staging. It must carry the existing schema, exact fixture and artifact binding, private run directory, and setup limits described by `probe-procedure.md`. Do not acquire private identity data before the later grant.

Record the fixture’s expected post-restoration state in the approval packet.

## Preflight

Coordinate the window so no package operation is active or scheduled to overlap it. Do not change global updater configuration.

```bash
set -euo pipefail
export LC_ALL=C

required=(RUN_ID PROBE_INSTALL_ROOT CANDIDATE_ARCHIVE CANDIDATE_BUILD_RECEIPT
  CANDIDATE_SHA256 REVIEWED_ARCHIVE_VERIFICATION
  PROBE_SYSTEM_STATE_ROOT PROBE_USER_STATE_ROOT PROBE_CONFIG
  PROBE_LAUNCHER PROBE_LAUNCH_ARGV_FILE PROBE_LAUNCH_ARGV_SHA256
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

for path in "$PROBE_INSTALL_ROOT" "$CANDIDATE_ARCHIVE" \
  "$CANDIDATE_BUILD_RECEIPT" "$REVIEWED_ARCHIVE_VERIFICATION" \
  "$PROBE_SYSTEM_STATE_ROOT" "$PROBE_USER_STATE_ROOT" "$PROBE_CONFIG" \
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

check_root_owned_ancestors "$PROBE_INSTALL_ROOT"
check_root_owned_ancestors "$PROBE_SYSTEM_STATE_ROOT"

sudo test -d "$PROBE_SYSTEM_STATE_ROOT"
test "$(sudo stat -c '%u:%g:%a' -- "$PROBE_SYSTEM_STATE_ROOT")" = "0:0:700"
test -d "$PROBE_USER_STATE_ROOT"
test -f "$PROBE_CONFIG"
test ! -L "$PROBE_CONFIG"
test "$(stat -c '%a:%h' -- "$PROBE_CONFIG")" = "600:1"
[[ "$PROBE_CONFIG" != "$OUTPUT_RUN_ROOT"/* ]]

package_line=$(pacman -Q -- claude-desktop-extra) || exit 1
test "$package_line" = "claude-desktop-extra 2.9939.4-1"
owner_line=$(pacman -Qo -- "$TARGET") || exit 1
test "$owner_line" = \
  "$TARGET is owned by claude-desktop-extra 2.9939.4-1"

hash_file() {
  local output digest
  output=$(sudo sha256sum -- "$1") || return 1
  read -r digest _ <<< "$output" || return 1
  printf '%s' "$digest"
}

check_no_xattrs() {
  local output
  output=$(sudo getfattr --absolute-names -d -m- -- "$1") || return 1
  test -z "$output"
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

for file in "$CANDIDATE_ARCHIVE" "$CANDIDATE_BUILD_RECEIPT" \
  "$REVIEWED_ARCHIVE_VERIFICATION" "$PROBE_LAUNCH_ARGV_FILE" \
  "$PROTECTED_ASSET_MANIFEST"; do
  test -f "$file"
  test ! -L "$file"
  test "$(stat -c '%h' -- "$file")" = "1"
done
test "$(hash_file "$CANDIDATE_ARCHIVE")" = "$CANDIDATE_SHA256"
test "$(hash_file "$PROBE_LAUNCH_ARGV_FILE")" = "$PROBE_LAUNCH_ARGV_SHA256"
test "$(hash_file "$PROTECTED_ASSET_MANIFEST")" = \
  "$PROTECTED_ASSET_MANIFEST_SHA256"

sudo test ! -e "$STAGE"
sudo test ! -L "$STAGE"
sudo test ! -e "$BACKUP_RUN_ROOT"
sudo test ! -L "$BACKUP_RUN_ROOT"
test ! -e "$OUTPUT_RUN_ROOT"
test ! -L "$OUTPUT_RUN_ROOT"
mv --help | grep -q -- '--exchange'
mv --help | grep -q -- '--no-copy'
```

Review `candidate-build.json`, the separately bound published revision, and the archive-verification record. Confirm the candidate hash and the complete unchanged-asset inventory.

Verify every manifest row by reading its fixed tab-delimited fields as data, checking that its absolute path is under `PROBE_INSTALL_ROOT`, and comparing SHA-256, owner, group, mode, link count, and size with `sha256sum` and `stat`. Require exactly one reviewed main executable, every reviewed native asset, and exactly one `chrome-sandbox`. Do not execute or evaluate manifest content. Save this verified manifest for restoration.

Quit Claude Desktop through its UI. Under the later grant, the exact selected application PID may be checked against the profile-specific `SingletonLock`; static review only establishes that the lock contains a PID. Do not infer that one PID proves every process has exited. If the current profile is not quiescent, stop. If another Desktop instance uses the shared installed resources, return for an operating decision. Do not enumerate unrestricted processes.

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

```bash
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

Immediately repeat the package, ownership, target identity, pristine hash, ACL, xattr, backup, and protected-asset manifest checks. Then exchange:

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

Unknown identities are a stop condition. If the pristine stage is lost, retain the protected backup and stop; do not use an unreviewed fallback.

## Launch and collection

```bash
PROBE_LAUNCH_ARGV=()
mapfile -d '' -t PROBE_LAUNCH_ARGV < "$PROBE_LAUNCH_ARGV_FILE" || exit 1
test "${#PROBE_LAUNCH_ARGV[@]}" -gt 0
test "${PROBE_LAUNCH_ARGV[0]}" = "$PROBE_LAUNCHER"
env PROVINGKIT_OBSERVER_CONFIG="$PROBE_CONFIG" "${PROBE_LAUNCH_ARGV[@]}"
```

After candidate launch and before waiting for bootstrap, submit this exact second prompt on the same recorded fixture:

```text
This is a disposable observer fixture. Reply exactly `PROBE_READY`. Do not use tools, inspect files, change settings, or begin other work.
```

The sidecar writes `bootstrap.json` into the selected private run directory after binding the existing query.
Under the later grant, the executor reads only that exact file, compares every binding field with the approved task, Code identity, and candidate bytes, then writes the matching `arm.json`.
The three query getters run only after arm acceptance. Collect for at most 30 seconds.

The reviewed helper is limited to the selected reported PID, three bounded `stat` reads, two executable opens, and 256 MiB of hashing. It must not read environments, command lines, unrelated processes, transcripts, or historical peers. Comparing a process report does not establish the Code query’s OS-process association; that remains unknown.

This window permits one arm only. A timeout or failed experiment requires a new plan and window, not an automatic retry.

After collection ends, whether successfully or unsuccessfully, quit Claude Desktop through its UI before any restoration check or exchange.
Verify that the exact selected PID has exited where that can be established, then verify that the current profile is quiescent.
One observed PID does not prove that all activity has ended. If the profile is not quiescent or an unknown or shared consumer still uses the installed resources, stop for an operating decision.

## Restore and verify

Before reversing, repeat `pacman -Q`, `pacman -Qo`, the complete protected-asset manifest, and these identity checks:

```bash
test "$(hash_file "$TARGET")" = "$CANDIDATE_SHA256"
test "$(sudo stat -c '%u:%g:%a:%h' -- "$TARGET")" = "0:0:644:1"
test "$(hash_file "$STAGE")" = "$PRISTINE_SHA256"
test "$(sudo stat -c '%u:%g:%a:%h:%s' -- "$STAGE")" = \
  "0:0:644:1:54910454"
test "$(hash_file "$BACKUP")" = "$PRISTINE_SHA256"
sudo cmp -s -- "$STAGE" "$BACKUP"
```

If the package version changed, ownership is unknown, or either archive identity fails, do not reverse the exchange.

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

Repeat package, ownership, complete manifest, and reviewed archive-verification checks. Restore-launch with the same argv and no observer binding:

```bash
env -u PROVINGKIT_OBSERVER_CONFIG "${PROBE_LAUNCH_ARGV[@]}"
```

Verify the selected profile opens and inspect the same fixture against the recorded restoration expectations. Restored bytes, protected assets, and task behavior are separate acceptance checks.

## Cleanup and retention

Immediately before deletion, repeat the exact `STAGE` candidate identity and `BACKUP` pristine identity, metadata, ACL, xattr, and comparison checks.

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

Retain mismatched artifacts and stop. Remove nothing else.

Raw output remains private through [Decide what the observer probe establishes](https://github.com/nisavid/provingkit/issues/281). After that decision approves a redacted summary and required evidence, delete only the exact manifest-listed fixture task, empty worktree, configuration, and output paths. No glob, broad recursive removal, permanent instrumentation, maintained observer deployment, periodic commitment, or expanded qualification is authorized.
