# Application staging and restoration

This runbook implements [Prepare and review the disposable observer probe](https://github.com/nisavid/provingkit/issues/278) as one operator-run window: create one fixture, protect the installed archive, atomically exchange in the reviewed candidate, run one bounded observer arm, stop it, restore the pristine archive, and verify restored behavior.
LIVE operation requires later authorization.

## Approval boundary

This runbook defines the application phases that consume
[Private probe data contracts](private-data-contracts.md), the normative home
for the selected-fixture projection, selected-executor invocation and result
variants, and cleanup-manifest schema.
[Private input construction](private-input-construction.md) defines how to
construct, validate, canonicalize, and exclusively create conforming bytes;
neither procedure defines alternative fields, states, reasons, or enum values.

[Authorize the disposable Desktop observer probe](https://github.com/nisavid/provingkit/issues/279)
must bind every variable to one exact value and every path variable to one exact
absolute path. The packet must not use `eval`, `source`, untrusted shell
expansion, or paths copied from this committed document:

- `RUN_ID`, beginning with `278-`.
- `PROBE_INSTALL_ROOT`, derived from package ownership.
- `CANDIDATE_ARCHIVE` and `GENERATED_BUILD_RECEIPT`, naming the same build output directory's `candidate.asar` and `build-receipt.json`.
- `PUBLISHED_BUILD_RECEIPT`, naming the reviewed revision's retained `candidate-build.json`.
- `CANDIDATE_SHA256`, `REVIEWED_ARCHIVE_VERIFICATION`, and
  `REVIEWED_ARCHIVE_VERIFICATION_SHA256`. The latter must equal
  `source.archiveVerification.sha256` in the populated private record.
- `PROBE_SYSTEM_STATE_ROOT`, a root-owned `0700` directory prepared only under the later authorization.
- `PROBE_USER_STATE_ROOT`, the existing private output root.
- `PROBE_CONFIG`, a private regular file outside the empty run directory.
- `CLEANUP_MANIFEST`, a private path outside the run directory that does not exist before the run.
- `LINUX_OBSERVATION_FILE`, a private path outside the run directory whose
  basename is exactly `selected-linux-executor-observation.json`.
- `PROBE_LAUNCHER`, its SHA-256 as `PROBE_LAUNCHER_SHA256`, and its reviewed device, inode, owner, group, mode, link count, and size as `PROBE_LAUNCHER_STAT`.
- The reviewed NUL-delimited `PROBE_LAUNCH_ARGV_FILE`, its reconstructed NUL-delimited SHA-256 as `PROBE_LAUNCH_ARGV_SHA256`, and its device, inode, owner, group, mode, link count, and size as `PROBE_LAUNCH_ARGV_STAT`.
- `PROTECTED_ASSET_MANIFEST`, its SHA-256, and the exact main-executable, complete native-asset, and `chrome-sandbox` inventory.
- The current profile, account, organization, new local Code task, new empty
  non-Git project directory, any app-created dedicated worktree and its approved
  expected entries, task ID, Code ID, constructed metadata path, approved
  process bindings, and task-restoration expectations.

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

## Normative private contracts

The normative selected-fixture projection and selected-executor invocation,
wrapper, and result variants are defined in
[Private probe data contracts](private-data-contracts.md#normative-private-contracts).
This runbook consumes those contracts; it does not define alternative fields,
states, reasons, or enum values.

## Fixture preparation

Before closing Claude Desktop or staging files, use the current signed-in
profile and a new dedicated empty directory that is not a Git repository or
worktree to create exactly one new top-level local Code task through the normal
new-task UI. Never fork, spawn, import, duplicate, or reuse a task. Resolve and
open the selected directory, record its exact real path, device, inode, UID,
GID, and mode, and require an empty nonrecursive entry list before creation. If
Desktop creates a dedicated worktree, record its identity and require only the
exact app-managed entries approved by the later grant. Do not resolve or invent
a worktree before creation. Stop and return for a decision on any unexpected
shape, activity, or identity change. Send the exact first prompt:

```text
This is a disposable observer fixture. Reply exactly `PROBE_READY`. Do not use tools, inspect files, change settings, or begin other work.
```

Reviewed source constructs the metadata path as
`path.join(Electron app.getPath("userData"), "claude-code-sessions",
currentAccountId, currentOrgId, taskId + ".json")`. Construct the exact path
from that source and the later selected profile, account, organization, and
task values. The exact app-data root remains an authorization binding gap; the
source-defined base is `claude-code-sessions`.
`getSessionFilePath` is an internal source method, not an approved callable UI
or API; do not invoke it. Do not enumerate the constructed path's parent
directory. Record its projected `sessionId`, `cliSessionId`, `cwd`,
`originCwd`, `worktreePath`, `spawnedFrom`, `dispatchParentId`,
`dispatchParentOrigin`, `forkedFromSessionId`, and `lineageDetached`; do not
export the raw metadata or a transcript.

Require matching task and Code IDs and require `cwd` to match the opened
project identity. Record `originCwd` and `worktreePath` as absent, present with
an empty string, or present with a nonempty value. Do not substitute the
project path for an absent or empty value or fabricate a worktree. Bind every
nonempty value to an approved opened-directory identity. Preserve each optional
lineage field's presence. If present, spawn, dispatch-parent, and fork fields
must be null and `lineageDetached` must be false. A non-null relation or true
`lineageDetached` is a stop condition. Absence remains absent and is not
evidence of confirmed nonrelation. Missing or changing required IDs, an
unexpected path, or unexpected activity is also a stop condition; do not
create another fixture or rescope.

Persisted nE metadata does not contain `backend.kind`. Record local creation
from the normal new-local-task UI provenance. Separately, the inspected adapter
source checks the live record for `backend.kind === "local"` with `sshConfig`
and `wslConfig` undefined before bootstrap or getter collection and refuses
unsupported routes. Static inspection of that guard is not live proof that a
particular run passed it.

The selected file provides no global proof that children do not exist or that
no unrelated task shares a repository, project, or worktree. Record
`selectedMetadataRelations` as `no-nonnull-relation-observed`,
`globalChildAbsence` as `not-established-from-selected-metadata`, and
`unrelatedSharingAbsence` as `not-established`. Current exclusive construction
and operator coordination remain cleanup gates, not global-sharing evidence.

Prepare `PROBE_CONFIG` before staging. It must carry the existing schema, exact
fixture and artifact binding, private run directory, and setup limits described
by `probe-procedure.md`. Construct and validate its exact bytes using
`private-input-construction.md`. Do not acquire private identity data before
the later grant.

Record the fixture's expected post-restoration state in the approval packet.
The bound cleanup-manifest path remains absent until the run reaches a terminal
state. If restoration is verified, complete or stop the distinct package-cleanup
phase before creating the manifest. If restoration was not required, create
the manifest without deleting any package path. If restoration is incomplete
or unverified, create the recovery manifest without deleting anything. Record
only identities and resources actually established. An uncertain task,
directory, worktree, file, or package path is retained pending an operational
decision; it is never treated as absent or discarded.

## Protected-asset manifest

`PROTECTED_ASSET_MANIFEST` is an LF-terminated tab-delimited data file with no
header or blank lines. Each row has exactly these eight nonempty columns:

```text
role<TAB>path<TAB>sha256<TAB>uid<TAB>gid<TAB>mode<TAB>links<TAB>size<LF>
```

`role` is exactly `main-executable`, `native-asset`, or `chrome-sandbox`.
`path` is the literal absolute pathname byte sequence: it is not quoted,
escaped, expanded, or normalized. A path containing a tab, LF, or CR is not
representable and must be rejected rather than escaped. `sha256` is 64
lowercase hexadecimal characters. `uid`, `gid`, `links`, and `size` are
canonical unsigned decimal integers; `links` is positive. `mode` is the three-
or four-digit octal spelling returned by `stat -c %a`.

The manifest contains exactly one `main-executable` row, exactly one
`chrome-sandbox` row, and one row for every reviewed native asset, with no
duplicate path or additional row. Its path set must equal the complete
package-derived inventory approved by issue 279. Completeness is established
during review of that inventory; a runtime scan must not invent or enlarge it.
The approved manifest hash binds the reviewed set.

## Manual phase supervision and shell recovery

This remains a manually supervised procedure. The operator, or an autonomous
control surface explicitly covered by the later grant, is the external phase
supervisor. The supervisor runs outside the shell that uses
`set -euo pipefail`; that shell is a supervised child process, not the holder
of recovery state. A shell exit therefore returns control to the supervisor.

The supervised phase boundaries are preflight, staging, exchange, candidate
launch and collection, candidate shutdown and quiescence, restoration and
restored verification, package cleanup, and cleanup-manifest creation. Before
each boundary, record the applicable existing failure-phase token and only the
resource identities, mutations, and absence checks already established. Use
the normative cleanup-manifest status, restoration, and package-cleanup fields;
this phase record does not define another schema.

On any nonzero command result, unexpected shell exit, or failed UI step, the
supervisor must:

1. Record the earliest failure without replacing an earlier `firstFailure`,
   stop the remaining commands in that phase, and stop collection. Do not retry
   a failed prompt, arm, getter, helper invocation, launch, exchange, deletion,
   or retained-file operation.
2. If Desktop may be running, request its normal UI shutdown, verify the
   selected PID has exited where that can be established, and establish current
   profile quiescence before any recovery action. No shell trap can establish
   application quiescence. If the authorized autonomous control surface is
   unavailable, stop and escalate to the human operator.
3. Retain every resource whose current state is known or uncertain. Do not
   reread configuration, output, sample, helper-result, or retained-evidence
   contents merely to reconstruct lost shell state.
4. If candidate exchange did not occur, establish whether the original archive
   bytes are unchanged and whether Desktop availability requires recovery.
   When unchanged bytes are established, perform no archive exchange. If
   Desktop remains closed, use the single restored launch only when covered by
   the later restoration-cycle grant, after the pristine, package, launcher,
   and quiescence checks pass. Record restoration as `not-required` only when
   no application or archive recovery obligation remains. If needed recovery
   is not covered, available, completed, or verified, record `incomplete` with
   status `recovery-required`. A changed or ambiguous archive, or an earlier
   launch with an ambiguous result, stops for a decision and does not
   authorize a retry. If exchange occurred or may have occurred, enter the
   already authorized restoration cycle only after quiescence. Recovery within
   that cycle does not authorize another candidate cycle or any launch or
   restart beyond its single grant.

A recovery shell is a fresh Bash process with `set -euo pipefail` and
`LC_ALL=C`. Before it performs any package mutation, the supervisor must:

1. Verify that the procedure revision is the immutable revision named by the
   grant. Manually repopulate the required variables from the existing
   validated private binding record and authorization packet. Do not use
   `source`, `eval`, shell-generated assignments, or newly acquired private
   data.
2. Repeat the required-variable, `RUN_ID`, absolute-path, component, no-symlink,
   and root-owned-ancestor validations from preflight. Reconstruct exactly
   `TARGET_DIR`, `TARGET`, `STAGE`, `BACKUP_RUN_ROOT`, `BACKUP`,
   `OUTPUT_RUN_ROOT`, and `PRISTINE_SHA256` from their reviewed definitions.
3. Re-enter verbatim from the reviewed revision the definitions of
   `hash_file`, `check_no_xattrs`, `check_root_archive_file`,
   `check_root_owned_directory`, `check_root_owned_ancestors`,
   `check_root_owned_parent_ancestors`,
   `check_reviewed_archive_verification`,
   `validate_protected_asset_manifest`, `check_reviewed_launcher`, and
   `load_reviewed_launch_argv`. Do not execute the rest of preflight as a
   definitions loader.
4. Re-establish `CANDIDATE_SIZE` only after the current candidate archive again
   matches `CANDIDATE_SHA256`. Recheck the current package version and
   ownership, protected-asset manifest and its bound hash, reviewed
   archive-verification record, and the exact target, stage, and backup
   identities applicable to the last verified phase.
5. Follow the restoration prechecks and remaining restoration steps from the
   first step not already verified. Never repeat a verified exchange or launch.
   A changed package, upgrade, ownership change, protected-asset change,
   missing archive, uncertain exchange state, identity mismatch, or failed
   restoration command stops recovery. Record `recovery-required`, retain all
   package and private resources, and return for the operational-restoration
   decision.

After a successful restoration exchange, or when unchanged archive bytes are
established but Desktop availability requires recovery, the one restored
launch authorized by the applicable restoration-cycle grant and its checks
remain necessary. No failure authorizes an extra launch. Package cleanup
remains prohibited until restoration is fully verified.

## Preflight

Issue 279 schedules one window and two full Desktop shutdown/launch cycles. The
window includes:

- the listed manual package, receipt, asset, launcher, argument, fixture, and
  directory checks;
- two submissions of the exact setup prompt;
- candidate staging and launch;
- getter initiation, asynchronous waiting, and settlement acceptance bounded by
  one 30-second monotonic observation deadline, without a hard-cancellation
  claim for uncancellable or synchronously blocking work;
- candidate shutdown, restoration, restored launch, and restoration checks;
- retained-artifact and cleanup-manifest construction.

The total duration is unmeasured. The operator chooses the window and
contingency and refuses to start if the available window is unsuitable. No
unsupported numerical total is evidence or an accepted deadline.

Coordinate the one current-profile window so no package operation is active or
scheduled to overlap it. Do not change global updater configuration.

```bash
set -euo pipefail
export LC_ALL=C

required=(RUN_ID PROBE_INSTALL_ROOT CANDIDATE_ARCHIVE
  GENERATED_BUILD_RECEIPT PUBLISHED_BUILD_RECEIPT CANDIDATE_SHA256
  REVIEWED_ARCHIVE_VERIFICATION REVIEWED_ARCHIVE_VERIFICATION_SHA256
  PROBE_SYSTEM_STATE_ROOT
  PROBE_USER_STATE_ROOT PROBE_CONFIG CLEANUP_MANIFEST
  PROBE_LAUNCHER PROBE_LAUNCHER_SHA256 PROBE_LAUNCHER_STAT
  LINUX_OBSERVATION_FILE PROBE_LAUNCH_ARGV_FILE PROBE_LAUNCH_ARGV_SHA256 PROBE_LAUNCH_ARGV_STAT
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
  "$LINUX_OBSERVATION_FILE" \
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
[[ "$LINUX_OBSERVATION_FILE" != "$OUTPUT_RUN_ROOT"/* ]]
test "${LINUX_OBSERVATION_FILE##*/}" = \
  "selected-linux-executor-observation.json"
test ! -e "$CLEANUP_MANIFEST"
test ! -L "$CLEANUP_MANIFEST"
test ! -e "$LINUX_OBSERVATION_FILE"
test ! -L "$LINUX_OBSERVATION_FILE"

package_line=$(pacman -Q -- claude-desktop-extra) || exit 1
test "$package_line" = "claude-desktop-extra 2.9939.4-1"
owner_line=$(pacman -Qo -- "$TARGET") || exit 1
test "$owner_line" = \
  "$TARGET is owned by claude-desktop-extra 2.9939.4-1"

hash_file() {
  local output digest marker
  output=$(sudo sha256sum -- "$1") || return 1
  if [[ "$output" == \\* ]]; then
    output="${output:1}"
  fi
  digest="${output:0:64}"
  marker="${output:64:2}"
  [[ "$digest" =~ ^[0-9a-f]{64}$ ]]
  [[ "$marker" = "  " || "$marker" = " *" ]]
  printf '%s' "$digest"
}

check_reviewed_archive_verification() {
  [[ "$REVIEWED_ARCHIVE_VERIFICATION_SHA256" =~ ^[0-9a-f]{64}$ ]]
  test -f "$REVIEWED_ARCHIVE_VERIFICATION"
  test ! -L "$REVIEWED_ARCHIVE_VERIFICATION"
  test "$(stat -c '%h' -- "$REVIEWED_ARCHIVE_VERIFICATION")" = "1"
  test "$(hash_file "$REVIEWED_ARCHIVE_VERIFICATION")" = \
    "$REVIEWED_ARCHIVE_VERIFICATION_SHA256"
}

validate_protected_asset_manifest() {
  local manifest="$1"
  local role path digest uid gid mode links size actual
  local cursor component last_byte
  local main_count=0 native_count=0 sandbox_count=0
  local -a components
  local -A seen_paths=()

  test -f "$manifest"
  test ! -L "$manifest"
  test "$(stat -c '%h' -- "$manifest")" = "1"
  test -s "$manifest"

  last_byte=$(
    tail -c 1 -- "$manifest" |
      od -An -tu1 |
      tr -d ' '
  ) || return 1
  test "$last_byte" = "10"

  awk -F '\t' '
    NF != 8 { exit 1 }
    {
      if (index($0, "\r") != 0) exit 1
      for (field = 1; field <= 8; field += 1) {
        if ($field == "") exit 1
      }
    }
    END {
      if (NR == 0) exit 1
    }
  ' "$manifest" || return 1

  while IFS=$'\t' read -r \
    role path digest uid gid mode links size; do
    case "$role" in
      main-executable)
        ((main_count += 1))
        ;;
      native-asset)
        ((native_count += 1))
        ;;
      chrome-sandbox)
        ((sandbox_count += 1))
        test "${path##*/}" = "chrome-sandbox"
        ;;
      *)
        return 1
        ;;
    esac

    [[ "$path" = /* ]]
    [[ "$path" = "$PROBE_INSTALL_ROOT"/* ]]
    [[ "$path" != *$'\t'* ]]
    [[ "$path" != *$'\n'* ]]
    [[ "$path" != *$'\r'* ]]
    [[ -z "${seen_paths[$path]+x}" ]]
    seen_paths["$path"]=1

    cursor="/"
    IFS=/ read -r -a components <<< "${path#/}" ||
      return 1
    for component in "${components[@]}"; do
      [[
        -n "$component" &&
        "$component" != "." &&
        "$component" != ".."
      ]]
      cursor="${cursor%/}/$component"
      sudo test ! -L "$cursor"
    done

    [[ "$digest" =~ ^[0-9a-f]{64}$ ]]
    [[ "$uid" =~ ^(0|[1-9][0-9]*)$ ]]
    [[ "$gid" =~ ^(0|[1-9][0-9]*)$ ]]
    [[ "$mode" =~ ^[0-7]{3,4}$ ]]
    [[ "$links" =~ ^[1-9][0-9]*$ ]]
    [[ "$size" =~ ^(0|[1-9][0-9]*)$ ]]

    sudo test -f "$path"
    sudo test ! -L "$path"
    actual=$(
      sudo stat -c '%u:%g:%a:%h:%s' -- "$path"
    ) || return 1
    test "$actual" = \
      "$uid:$gid:$mode:$links:$size"
    test "$(hash_file "$path")" = "$digest"
  done < "$manifest"

  test "$main_count" = "1"
  test "$sandbox_count" = "1"
  test "$native_count" -gt 0
}

check_no_xattrs() {
  local output
  output=$(sudo getfattr --absolute-names -d -m- -- "$1") || return 1
  test -z "$output"
}

check_root_archive_file() {
  local path="$1" expected_sha256="$2" expected_size="$3"
  local actual acl

  [[ "$expected_sha256" =~ ^[0-9a-f]{64}$ ]]
  [[ "$expected_size" =~ ^(0|[1-9][0-9]*)$ ]]
  sudo test -f "$path"
  sudo test ! -L "$path"
  actual=$(sudo stat -c '%u:%g:%a:%h:%s' -- "$path") || return 1
  test "$actual" = "0:0:644:1:$expected_size"
  acl=$(sudo getfacl -cp -- "$path") || return 1
  test "$acl" = $'user::rw-\ngroup::r--\nother::r--'
  check_no_xattrs "$path"
  test "$(hash_file "$path")" = "$expected_sha256"
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

check_reviewed_archive_verification
cmp -s -- "$GENERATED_BUILD_RECEIPT" "$PUBLISHED_BUILD_RECEIPT"
test "$(hash_file "$CANDIDATE_ARCHIVE")" = "$CANDIDATE_SHA256"
CANDIDATE_SIZE=$(stat -c '%s' -- "$CANDIDATE_ARCHIVE") || exit 1
[[ "$CANDIDATE_SIZE" =~ ^(0|[1-9][0-9]*)$ ]]
test "$(hash_file "$PROTECTED_ASSET_MANIFEST")" = \
  "$PROTECTED_ASSET_MANIFEST_SHA256"
validate_protected_asset_manifest \
  "$PROTECTED_ASSET_MANIFEST"
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
unchanged-asset inventory matches it. Every later receipt comparison or
archive-evidence check must call
`check_reviewed_archive_verification` again and compare the current record
bytes with `REVIEWED_ARCHIVE_VERIFICATION_SHA256`; an earlier successful
comparison cannot be reused.

At every later point that requires the complete protected-asset check, run
`validate_protected_asset_manifest "$PROTECTED_ASSET_MANIFEST"` again after
rechecking the manifest file's bound SHA-256. Do not evaluate a row as shell
text or use it to construct a command string.

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

check_root_archive_file \
  "$BACKUP" "$PRISTINE_SHA256" "54910454"
sudo cmp -s -- "$TARGET" "$BACKUP"
```

## Atomic candidate exchange

The build receipts must still compare byte for byte immediately before the
candidate is copied into the package-owned staging path.

```bash
check_reviewed_archive_verification
cmp -s -- "$GENERATED_BUILD_RECEIPT" "$PUBLISHED_BUILD_RECEIPT"
test "$(hash_file "$CANDIDATE_ARCHIVE")" = "$CANDIDATE_SHA256"

sudo install -o 0 -g 0 -m 0644 -- "$CANDIDATE_ARCHIVE" "$STAGE"
check_root_archive_file \
  "$STAGE" "$CANDIDATE_SHA256" "$CANDIDATE_SIZE"
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
check_reviewed_archive_verification
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
that exact file, validates every generated bootstrap value, compares every
binding field with the approved task, Code identity, candidate bytes,
configuration digest, and clock domain, then exclusively creates the matching
`arm.json`. The arm echoes every `BINDING_KEYS` field, including the Linux boot
domain. Follow the exact encoding and file-identity procedure in
`private-input-construction.md`. The three query getters run only after arm
acceptance. Do not start a getter or accept a settlement at or after the
30-second monotonic observation deadline. Clamp every asynchronous wait to the
lesser of its two-second limit and the remaining window. A timed-out or
synchronously blocked getter cannot be forcibly cancelled and can outlive the
deadline; do not treat that possibility as authority for another call or
sample.

The reviewed helper is limited to two metadata checks of the selected numeric
PID path, one owned `O_DIRECTORY | O_NOFOLLOW` descriptor open, seven
descriptor metadata checks, three `stat` opens reading at most 4,096 bytes
each, two `exe` opens, and at most 256 MiB hashed. Every child open uses only a
fixed name beneath the retained descriptor after an immediate identity,
ownership, and freshness recheck. It must not re-resolve a child through the
numeric PID path or read environments, command lines, unrelated processes,
transcripts, or historical peers. Comparing a process report does not establish
the Code query's OS-process association; that remains unknown.

Construct the one authorized helper invocation from
[the normative contract](private-data-contracts.md#normative-private-contracts)
and apply the exact byte procedure in
[private input construction](private-input-construction.md). Invoke the
exported helper at most once and only when an actual usable sample supplies the
sequence and complete accepted binding. Validate its in-memory return against
one normative result variant, construct the normative wrapper, and serialize
only that wrapper into `LINUX_OBSERVATION_FILE`.

If no usable sample exists, the helper is not called. If the helper is not
reached, is deliberately not called, or retained-file creation or validation
fails, do not invoke it again to fill the cleanup manifest. Record the
retained-evidence state and terminal reason defined in
[the cleanup contract](private-data-contracts.md#private-cleanup-manifest-and-retention).
Retain any created
but unvalidated path as an unresolved resource.

A valid retained file is a private regular single-link `0600` file no larger
than 16384 bytes. Record its exact identity and digest in the cleanup manifest.
Do not serialize a caught error, exception text, arbitrary raw object, or fake
binding.

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

Repeat the package, ownership, complete-manifest, receipt, and reviewed
archive-verification checks, including a fresh
`check_reviewed_archive_verification` call. Immediately before the restored
launch, recheck the package and pristine target, revalidate the launcher and
its root-owned ancestors, and reconstruct the argument array through a newly
opened stable descriptor. Do not reuse the candidate launch's array or reopen
the argument path after validation.

```bash
package_line=$(pacman -Q -- claude-desktop-extra) || exit 1
test "$package_line" = "claude-desktop-extra 2.9939.4-1"
owner_line=$(pacman -Qo -- "$TARGET") || exit 1
test "$owner_line" = \
  "$TARGET is owned by claude-desktop-extra 2.9939.4-1"
test "$(hash_file "$TARGET")" = "$PRISTINE_SHA256"
check_reviewed_archive_verification

PROBE_LAUNCH_ARGV=()
load_reviewed_launch_argv PROBE_LAUNCH_ARGV
check_reviewed_launcher
env -u PROVINGKIT_OBSERVER_CONFIG "${PROBE_LAUNCH_ARGV[@]}"
```

Verify the selected profile opens and inspect the same fixture against the
recorded restoration expectations. Restored bytes, protected assets, and task
behavior are separate acceptance checks.

## Package cleanup

Package cleanup is a distinct phase before cleanup-manifest creation. It may
remove only `STAGE`, `BACKUP`, and `BACKUP_RUN_ROOT`, and only after restoration
is `verified`. It does not require the issue 281 private-cleanup decision. A
`not-required`, incomplete, or otherwise unverified restoration authorizes no
package deletion. Incomplete restoration also prohibits every private, task,
project, worktree, and manifest deletion.

Immediately before deleting the package staging copy and protected backup,
repeat the exact `STAGE` candidate identity and `BACKUP` pristine identity,
metadata, ACL, xattr, and comparison checks.

```bash
check_root_archive_file \
  "$BACKUP" "$PRISTINE_SHA256" "54910454"
sudo cmp -s -- "$TARGET" "$BACKUP"

check_root_archive_file \
  "$STAGE" "$CANDIDATE_SHA256" "$CANDIDATE_SIZE"
sudo rm -- "$STAGE"
sudo test ! -e "$STAGE"
sudo test ! -L "$STAGE"

check_root_archive_file \
  "$BACKUP" "$PRISTINE_SHA256" "54910454"
sudo cmp -s -- "$TARGET" "$BACKUP"
sudo rm -- "$BACKUP"
sudo test ! -e "$BACKUP"
sudo test ! -L "$BACKUP"

sudo rmdir -- "$BACKUP_RUN_ROOT"
sudo test ! -e "$BACKUP_RUN_ROOT"
sudo test ! -L "$BACKUP_RUN_ROOT"
```

After each command, record only the resource state established by the command
and its absence check. On an identity-precheck mismatch or failure before any
deletion attempt, record a new `package-cleanup` failure through the existing
status rules, preserving `firstFailure` and the top-level earliest stopped
phase, set `packageCleanup.state` to `retained`, and stop without retrying. If
removal was attempted but none was verified, use `failed`; if at least one
removal was verified before failure, use `partial`. Retain every resource
still known or possibly present. Attempt package deletion only after verified
restoration, and remove no other package-owned path.

## Private cleanup manifest and retention

After package cleanup ends, or at terminal stop when package deletion is
prohibited, create the cleanup manifest and apply the retention handling
defined by
[Private probe data contracts](private-data-contracts.md#private-cleanup-manifest-and-retention).
Use only facts established during this run; do not introduce alternative
fields, states, reasons, or enum values.
