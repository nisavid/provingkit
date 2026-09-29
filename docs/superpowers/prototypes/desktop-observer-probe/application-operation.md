# Application staging and restoration

This runbook implements [Prepare and review the disposable observer probe](https://github.com/nisavid/provingkit/issues/278) as one operator-run window: create one fixture, protect the installed archive, atomically exchange in the reviewed candidate, run one bounded observer arm, stop it, restore the pristine archive, and verify restored behavior.
LIVE operation requires later authorization.

## Approval boundary

This document is the normative home for the selected-fixture projection, the
selected-executor invocation and result variants, and the cleanup-manifest
schema. [Private input construction](private-input-construction.md) defines how
to construct, validate, canonicalize, and exclusively create bytes that conform
to these contracts; it does not define alternative fields, states, reasons, or
enum values.

[Authorize the disposable Desktop observer probe](https://github.com/nisavid/provingkit/issues/279)
must bind every variable to one exact value and every path variable to one exact
absolute path. The packet must not use `eval`, `source`, untrusted shell
expansion, or paths copied from this committed document:

- `RUN_ID`, beginning with `278-`.
- `PROBE_INSTALL_ROOT`, derived from package ownership.
- `CANDIDATE_ARCHIVE` and `GENERATED_BUILD_RECEIPT`, naming the same build output directory's `candidate.asar` and `build-receipt.json`.
- `PUBLISHED_BUILD_RECEIPT`, naming the reviewed revision's retained `candidate-build.json`.
- `CANDIDATE_SHA256` and the reviewed archive-verification record.
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

The selected metadata projection has exactly this shape:

```json
{
  "sessionId": "exact selected task ID",
  "cliSessionId": "exact selected Code session ID",
  "cwd": "exact selected real directory",
  "optionalPathStates": {
    "originCwd": "absent, empty, or exact approved absolute real-directory path",
    "worktreePath": "absent, empty, or exact approved absolute real-directory path"
  },
  "optionalFieldPresence": {
    "presentNull": ["actual subset of spawnedFrom, dispatchParentId, dispatchParentOrigin, and forkedFromSessionId present with null"],
    "presentFalse": ["lineageDetached only when actually present with false"],
    "absent": ["every allowed optional field actually absent from the selected JSON"]
  }
}
```

Its relation evidence is exactly:

```json
{
  "selectedMetadataRelations": "no-nonnull-relation-observed",
  "globalChildAbsence": "not-established-from-selected-metadata",
  "unrelatedSharingAbsence": "not-established"
}
```

The selected-executor invocation has exactly these keys:

```json
{
  "afterSequence": 0,
  "expectedBinding": "exact complete accepted bootstrap binding object",
  "expectedUid": 0,
  "maximumAgeMs": 30000,
  "runDirectory": "exact absolute OUTPUT_RUN_ROOT",
  "sequence": 0
}
```

`sequence` is an actually selected integer from 1 through 3,
`afterSequence` is exactly `sequence - 1`, and `expectedUid` is the selected
Desktop user's nonnegative integer UID. Construct this object only after a
usable selected sample exists. Do not invent a sequence, binding, task ID, Code
ID, or sample to make the helper callable.

The retained wrapper has exactly these top-level fields:

```json
{
  "schema": "provingkit.desktop-probe-linux-observation.v1",
  "source": {
    "publishedRevision": "immutable reviewed Git revision",
    "publishedBuildReceiptSha256": "lowercase SHA-256",
    "candidateSha256": "receipt candidate SHA-256",
    "moduleSha256": "receipt sidecar SHA-256"
  },
  "run": {
    "runId": "exact RUN_ID",
    "targetTaskId": "exact selected task ID",
    "targetCodeSessionId": "exact selected Code ID"
  },
  "sample": {
    "runDirectory": "exact absolute OUTPUT_RUN_ROOT",
    "sequence": 0,
    "expectedBinding": "exact complete accepted bootstrap binding object"
  },
  "result": "one exact result variant below"
}
```

The two unknown result variants are exactly:

```json
{"state":"unknown","reason":"selected-sample-unavailable-or-changed","qualification":"unqualified","queryToOsAssociation":"unknown"}
```

```json
{"state":"unknown","reason":"linux-identity-unavailable-or-changed","qualification":"unqualified","queryToOsAssociation":"unknown"}
```

`selected-sample-unavailable-or-changed` also covers failure to acquire the
Linux boot domain before sample selection. Without that domain the helper
cannot validate a selected sample, so this reason does not claim that the
sample file is missing. `linux-identity-unavailable-or-changed` applies only
after a sample has passed boot-domain, binding, and freshness selection and
process-identity acquisition has begun.

The observed result has exactly this shape:

```json
{
  "state": "observed-partial",
  "qualification": "unqualified",
  "sampleEvidence": {
    "binding": "exact complete revalidated sample binding",
    "sequence": 0,
    "observedAt": 0,
    "observedAtMonotonicMs": 0,
    "collection": {
      "startedAt": 0,
      "endedAt": 0,
      "startedAtMonotonicMs": 0,
      "endedAtMonotonicMs": 0
    }
  },
  "selectedReport": {
    "taskId": "exact selected task ID",
    "cliPid": 0,
    "cliPidAtMs": null,
    "cliReportedVersion": null,
    "currentCodeSessionId": "exact selected Code ID",
    "queryGeneration": 0,
    "historicProvenance": "unknown",
    "queryToOsAssociation": "unknown",
    "reportBasis": "manager-retained-report; not independent OS association"
  },
  "linuxIdentity": {
    "pid": 0,
    "processStartTicks": "observed decimal start ticks",
    "ownerUid": 0,
    "executable": {
      "dev": "decimal device",
      "ino": "decimal inode",
      "size": "decimal size",
      "sha256": "lowercase SHA-256"
    }
  },
  "queryToOsAssociation": "unknown"
}
```

In `observed-partial`, `cliPidAtMs` is independently either JSON `null` or the
actual nonnegative safe integer reported by the producer.
`cliReportedVersion` is independently either JSON `null` or the actual
nonempty bounded text reported by the producer. Preserve either null exactly.
Do not invent a timestamp or version, borrow one from another producer, or
reclassify an otherwise valid observation because either field is null.

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
state. Create the manifest after restoration is verified, when restoration was
not required, or as the recovery record when restoration is incomplete. Record
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
  REVIEWED_ARCHIVE_VERIFICATION PROBE_SYSTEM_STATE_ROOT
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
unchanged-asset inventory matches it.

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

Construct the one authorized helper invocation from the normative contract
above and apply the exact byte procedure in
[private input construction](private-input-construction.md). Invoke the
exported helper at most once and only when an actual usable sample supplies the
sequence and complete accepted binding. Validate its in-memory return against
one normative result variant, construct the normative wrapper, and serialize
only that wrapper into `LINUX_OBSERVATION_FILE`.

If no usable sample exists, the helper is not called. If the helper is not
reached, is deliberately not called, or retained-file creation or validation
fails, do not invoke it again to fill the cleanup manifest. Record the
retained-evidence state and terminal reason defined below. Retain any created
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

Package cleanup is permitted only after restoration has been verified. If
restoration is incomplete, retain `TARGET`, `STAGE`, `BACKUP`, every private
artifact, and the cleanup manifest recovery record without deleting anything.

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

Raw output remains private through
[Decide what the observer probe establishes](https://github.com/nisavid/provingkit/issues/281).
At the terminal stop, exclusively create and validate `CLEANUP_MANIFEST` as a
private regular, single-link `0600` file unless its creation or validation
fails. It is an inventory and recovery record, not an executable cleanup
script.

Use schema `provingkit.desktop-probe-cleanup.v2`. The top-level shape is:

```json
{
  "schema": "provingkit.desktop-probe-cleanup.v2",
  "createdAt": "RFC-3339 timestamp",
  "runId": "exact RUN_ID",
  "status": "one exact status variant below",
  "restoration": "one exact restoration variant below",
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
  "fixture": "one exact fixture variant below",
  "configuration": "one exact configuration variant below",
  "output": "one exact output variant below",
  "retainedEvidence": "one exact retained-evidence variant below",
  "unresolvedResources": []
}
```

A completed run uses:

```json
{
  "state": "completed",
  "reason": "completed",
  "phase": "complete",
  "firstFailure": {
    "state": "absent"
  },
  "laterFailures": []
}
```

A stopped run uses:

```json
{
  "state": "stopped",
  "reason": "phase-failed",
  "phase": "exact earliest failed phase",
  "firstFailure": {
    "state": "present",
    "reason": "phase-failed",
    "phase": "same exact earliest failed phase"
  },
  "laterFailures": [
    {
      "reason": "phase-failed",
      "phase": "exact later failed phase"
    }
  ]
}
```

A run whose restoration cannot be completed or verified uses:

```json
{
  "state": "recovery-required",
  "reason": "restoration-incomplete",
  "phase": "restoration",
  "firstFailure": {
    "state": "present",
    "reason": "phase-failed or restoration-incomplete",
    "phase": "exact earliest failed phase"
  },
  "laterFailures": [
    {
      "reason": "phase-failed or restoration-incomplete",
      "phase": "exact later failed phase"
    }
  ]
}
```

The exact failure phases are `preflight`, `staging`, `exchange`, `setup`,
`fixture-creation`, `fixture-query`, `configuration-creation`,
`configuration-validation`, `output-root-creation`,
`output-root-validation`, `candidate-launch`, `bootstrap`, `arm`, `sample`,
`helper-invocation`, `helper-result-validation`,
`retained-evidence-creation`, `retained-evidence-validation`, `restoration`,
`cleanup-manifest-creation`, and `cleanup-manifest-validation`.
`restoration-incomplete` is used only with phase `restoration`; every other
failure uses `phase-failed`.

`firstFailure` preserves the earliest terminal failure. `laterFailures` lists
only later failures, in occurrence order, and remains empty when there were
none. Restoration has outcome priority: an incomplete or unverified
restoration changes the top-level status to `recovery-required` /
`restoration-incomplete`, while `firstFailure` continues to preserve an
earlier stop such as `sample` or `exchange`. Without an incomplete
restoration, the earliest failure remains the top-level stopped phase. A later
absent helper, retention failure, or manifest failure does not replace it.

Failure to acquire or validate the host boot UUID during setup is phase
`setup`. A missing, malformed, or mismatched boot UUID in a bootstrap, arm, or
sample record is assigned to the corresponding `bootstrap`, `arm`, or
`sample` phase. This classification does not change the established metadata
or Linux observation schemas.

When no candidate exchange occurred, restoration is:

```json
{
  "state": "not-required",
  "recoveryRecord": {
    "state": "absent"
  }
}
```

After the complete restoration checks pass, restoration is:

```json
{
  "state": "verified",
  "verifiedAt": "RFC-3339 timestamp",
  "recoveryRecord": {
    "state": "absent"
  }
}
```

If restoration cannot be completed or verified, restoration is:

```json
{
  "state": "incomplete",
  "recoveryRecord": {
    "state": "required",
    "lastVerifiedStep": "literal last verified restoration step",
    "knownPackageArtifacts": [
      {
        "role": "target, stage, or backup",
        "path": "exact known path",
        "knownIdentity": {
          "onlyActuallyVerifiedFields": "actual values"
        }
      }
    ],
    "retention": "all-package-and-private-artifacts",
    "nextDecision": "operational-restoration"
  }
}
```

`knownPackageArtifacts` lists only package paths that actually exist or whose
continued existence is uncertain. `knownIdentity` contains only fields
actually verified at the stop. Do not infer a digest, identity, or absence.
Restoration state `incomplete` prohibits all package, task, configuration,
output, retained-evidence, project, worktree, and manifest deletion.

An established fixture uses this variant:

```json
{
  "state": "established",
  "profile": "exact selected profile identity",
  "accountId": "exact selected account identity",
  "organizationId": "exact selected organization identity",
  "taskId": "exact disposable task identity",
  "codeId": "exact Code session identity",
  "metadataPath": "exact absolute selected metadata path",
  "creationProvenance": {
    "route": "normal-new-local-task-ui",
    "createdAt": "RFC-3339 timestamp",
    "preCreationInspection": "nonrecursive-empty",
    "unexpectedActivity": "none-observed"
  },
  "selectedMetadata": {
    "sessionId": "exact taskId",
    "cliSessionId": "exact codeId",
    "cwd": "exact real directory path",
    "optionalPathStates": {
      "originCwd": "absent, empty, or exact approved real-directory path",
      "worktreePath": "absent, empty, or exact approved real-directory path"
    },
    "optionalFieldPresence": {
      "presentNull": [
        "exact subset of spawnedFrom, dispatchParentId, dispatchParentOrigin, and forkedFromSessionId present with null"
      ],
      "presentFalse": [
        "lineageDetached only when present with false"
      ],
      "absent": [
        "every allowed optional field absent from the selected JSON"
      ]
    }
  },
  "relationEvidence": {
    "selectedMetadataRelations": "no-nonnull-relation-observed",
    "globalChildAbsence": "not-established-from-selected-metadata",
    "unrelatedSharingAbsence": "not-established",
    "operatorCoordinationAt": "RFC-3339 timestamp"
  },
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
    "state": "absent"
  }
}
```

If Desktop created a verified worktree, replace only the `worktree` object
with:

```json
{
  "state": "present",
  "path": "exact absolute app-created worktree path",
  "device": "decimal device",
  "inode": "decimal inode",
  "uid": "decimal owner",
  "gid": "decimal group",
  "mode": "octal mode",
  "creation": "app-created",
  "dedication": "dedicated",
  "validatedEntries": ["actual approved nonrecursive entries"]
}
```

For each optional metadata path, write exactly `absent`, `empty`, or its
approved nonempty real-directory path. Do not add a path or worktree identity
for an absent or empty field. The lineage presence arrays contain only fields
actually present with the stated value; absent fields belong only in
`absent`.

Before the complete fixture identity is established, use this variant:

```json
{
  "state": "not-created, partial, or uncertain",
  "createdResources": [],
  "uncertainResources": [],
  "selectedMetadata": "one exact incomplete selected-metadata variant below",
  "retention": "through-issue-281 or pending-operational-decision"
}
```

When selected metadata was not acquired, use:

```json
{
  "state": "absent",
  "reason": "not-acquired or query-failed"
}
```

When a query returned data that did not establish the complete selected
metadata identity, use:

```json
{
  "state": "unvalidated",
  "knownIdentity": {
    "onlyActuallyEstablishedFields": "actual values"
  },
  "reason": "query-unvalidated"
}
```

`createdResources` lists only resources known to have been created. Each entry
has role `project-directory`, `desktop-task`, or `app-created-worktree` and
contains only the path, identifier, and identity fields actually established.
`uncertainResources` records a possibly created task, project path, or
worktree as:

```json
{
  "role": "project-directory, desktop-task, or app-created-worktree",
  "knownIdentity": {
    "onlyActuallyKnownFields": "actual values"
  },
  "disposition": "retain-pending-operational-decision"
}
```

Do not fabricate a task ID, Code ID, metadata path, selected projection,
project path, or worktree path. An uncertain resource is never moved to
`createdResources`, declared absent, or deleted merely to complete the
manifest.

Configuration is absent only when absence was established:

```json
{
  "state": "absent"
}
```

A configuration that passed the accepted identity checks is:

```json
{
  "state": "present",
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
}
```

If configuration creation may have left a path that did not pass validation,
use:

```json
{
  "state": "unvalidated",
  "path": "exact known path",
  "knownIdentity": {
    "onlyActuallyVerifiedFields": "actual values"
  },
  "disposition": "retain-pending-operational-decision"
}
```

Add that path to `unresolvedResources`. Do not declare the configuration
absent merely because creation or validation failed.

Output is:

```json
{
  "root": {
    "state": "absent"
  },
  "artifactStates": {
    "bootstrap": "absent",
    "arm": "absent",
    "samples": "absent"
  },
  "emittedFiles": []
}
```

Use an absent root only when absence was established. A root that passed the
accepted identity checks is:

```json
{
  "state": "present",
  "path": "exact absolute OUTPUT_RUN_ROOT",
  "type": "directory",
  "device": "decimal device",
  "inode": "decimal inode",
  "uid": "decimal owner",
  "gid": "decimal group",
  "mode": "0700"
}
```

If output-root creation may have left a path that did not pass validation,
use:

```json
{
  "state": "unvalidated",
  "path": "exact known path",
  "knownIdentity": {
    "onlyActuallyVerifiedFields": "actual values"
  },
  "disposition": "retain-pending-operational-decision"
}
```

Add that path to `unresolvedResources`. Each artifact state is exactly
`absent`, `present-validated`, or `present-unvalidated`. Use `absent` only when
absence was established. `emittedFiles` contains only files that actually
exist and passed the identity checks:

```json
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
```

A created or possibly created output path that did not pass validation is not
fabricated into `emittedFiles`. Record only its known identifiers in
`unresolvedResources` and retain it.

Retained evidence is absent when no valid retained file was established:

```json
{
  "state": "absent",
  "reason": "not-reached, no-usable-selected-sample, helper-not-called, helper-invocation-failed, helper-result-unvalidated, retention-creation-failed, or retention-validation-failed"
}
```

A retained file that passed the accepted identity checks uses:

```json
{
  "state": "present",
  "files": [
    {
      "role": "selected-linux-executor-observation",
      "purpose": "strictly serialized selected-executor helper return",
      "path": "exact absolute LINUX_OBSERVATION_FILE outside OUTPUT_RUN_ROOT",
      "type": "regular-file",
      "device": "decimal device",
      "inode": "decimal inode",
      "uid": "decimal owner",
      "gid": "decimal group",
      "mode": "0600",
      "links": 1,
      "size": "decimal bytes from 1 through 16384",
      "sha256": "lowercase SHA-256"
    }
  ]
}
```

Use `no-usable-selected-sample` when no sample can truthfully supply the
binding and sequence. Use `helper-not-called` only when a usable sample existed
but the authorized helper invocation did not occur. Use
`helper-invocation-failed` when the helper invocation threw or otherwise
failed to return. Use `helper-result-unvalidated` when it returned a value
that could not be validated under the unchanged Linux observation schema.
Use `retention-creation-failed` or `retention-validation-failed` when the
corresponding file operation did not establish a valid retained file. Do not
call the helper again for any of these states. A possibly created or invalid
retained path belongs in `unresolvedResources` and remains retained.

Every file array contains only actual files. Empty arrays remain empty; they
never contain placeholders, patterns, ranges, or expected future files.
`unresolvedResources` records every known or possibly created resource whose
identity, existence, or validity is insufficient for cleanup:

```json
{
  "role": "exact resource role",
  "knownIdentity": {
    "onlyActuallyKnownIdentifiersOrIdentityFields": "actual values"
  },
  "disposition": "retain-pending-operational-decision"
}
```

Do not add an unknown path, identifier, digest, or identity field merely to
make an entry look complete. Do not read private configuration, output, helper
results, or retained evidence solely to populate missing manifest fields.
Use only identities already established by the authorized run.

If cleanup-manifest creation or validation fails, retain every resource and
return the failure without retrying or creating a replacement at another
path. The terminal report uses the same status schema even though no valid
manifest exists. A manifest failure is the first failure when none preceded
it; otherwise, append it to `laterFailures`. If restoration is incomplete,
`recovery-required` / `restoration-incomplete` retains top-level priority. A
possibly created or invalid manifest path is itself retained using only its
known path or identity.

No failed setup, query, creation, launch, sampling, helper, retention,
restoration, or manifest operation is retried to fill the manifest. Manifest
recording does not authorize another UI action, helper invocation, candidate
launch, private-data read, external request, or other live effect. Nothing in
this section broadens the run’s accepted permissions.

No cleanup is authorized without an exclusively created, validated manifest
and the later issue 281 decision. Issue 281 may approve deletion only after
restoration is `verified` or `not-required`, no applicable resource remains
unresolved, and it names the reviewed cleanup manifest and SHA-256, the exact
task identity when one is known, and the exact roles or paths to remove.
Anything unnamed or uncertain remains retained.

The later authorized cleanup input is a manually populated private packet for
this run. This section does not authorize implementing or running a general
cleanup tool.

Source inspection found that `LocalSessions.delete(sessionId)` delegates to
`manager.deleteSession` with `userInitiated: true`, and manager teardown may
cascade to linked tasks, associated worktrees, and transcripts. Do not call
either internal method, invoke a private API, or add cleanup instrumentation.
Before deletion, reread only the exact selected metadata path and revalidate its
task and Code IDs, `cwd`, optional-path states, and spawn, dispatch-parent,
fork, and `lineageDetached` values when present. Preserve absent and empty
fields exactly, and stop on a non-null relation or true `lineageDetached`.
Reconfirm exclusive fixture construction, current operator coordination,
dedicated directory identities, and absence of unexpected activity. Do not
claim global child or sharing absence from that one file, scan all tasks, or
invoke an internal family or cleanup API.

Use only Desktop's normal task-deletion UI. Proceed only when the live UI shows
the selected disposable fixture and its confirmation establishes the managed
removal scope, including any linked-task and worktree effect, as matching the
recorded fixture. UI labels and controls are not assumed by this runbook. If
the control is absent, the selected identity cannot be confirmed, the managed
scope cannot be established, or the confirmation indicates broader scope,
retain the fixture and return for an operational decision. The approved cleanup
accepts managed removal of that task's own transcript and dedicated worktree.
If any broader side effect is shown or observed, stop without continuing file
cleanup and report it.

After the exact UI deletion, confirm through the selected task route that the
task is absent and compare the recorded fixture directory identities and
explicitly coordinated unrelated work with their recorded expectations. This
is not a global absence-of-change claim. Do not manually delete Desktop private
profile stores, task metadata, transcripts, other worktrees, or any
application-managed residual path.

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

Process an approved retained-evidence file as its own manifest entry. Require
exact equality with `LINUX_OBSERVATION_FILE`, require that it is outside the
output root and has the fixed basename
`selected-linux-executor-observation.json`, and repeat its type, identity,
ownership, mode, link-count, size, SHA-256, absolute-path, and no-symlink
checks. Run `unlink -- "$LINUX_OBSERVATION_FILE"` only when issue 281 names
that exact entry. Verify both `test ! -e "$LINUX_OBSERVATION_FILE"` and
`test ! -L "$LINUX_OBSERVATION_FILE"` afterward. A mismatch retains the file.

If an established fixture's exact manifest-listed project remains after the UI
operation, compare its device, inode, owner, group, and mode with the manifest,
confirm it is still dedicated to the deleted fixture, and verify it is empty.
Apply the same checks to a worktree only when the established fixture records
its state as `present`. A partial or uncertain fixture supplies no cleanup
authority for a task, project, or worktree; retain every such resource pending
an operational decision. Only then may
`rmdir -- "$EXACT_DIRECTORY"` remove that one directory. Do not unlink
directory contents to make it empty. A missing recorded directory is an
accepted managed effect; a nonempty, changed, shared, or differently owned
directory is retained.

The cleanup manifest itself remains private decision evidence unless issue 281
separately binds its exact path, external hash and file identity, and approves
unlinking it last. No glob, broad recursive removal, permanent instrumentation,
maintained observer deployment, periodic commitment, or expanded qualification
is authorized.
