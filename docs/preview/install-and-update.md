# Install and update the pinned unsigned preview

Install the six Provingkit plugins from the target artifacts of
[`preview-8acd0e2af1f4`](https://github.com/nisavid/provingkit/releases/tag/preview-8acd0e2af1f4).
The qualified source is commit
[`8acd0e2af1f4508a0e2358d8e01f6a3db7a78ce3`](https://github.com/nisavid/provingkit/commit/8acd0e2af1f4508a0e2358d8e01f6a3db7a78ce3).
Its artifacts remain fixed when this guide changes.

For a Linux rollout, first follow [installation preparation](linux-installation.md)
to inventory existing providers and retain recovery records. Agents use
`capturing-agent-procedures`, load this guide at its reviewed commit, and record
that revision in the rollout or maintenance handoff.
[Rollout #70](https://github.com/nisavid/provingkit/issues/70) owns live adoption;
[maintenance #72](https://github.com/nisavid/provingkit/issues/72) consumes its
verified installed state.

## Select and download a target

The commands below use a POSIX shell, `curl`, GNU `tar`, `sha256sum`, and
Python 3 on Linux.

The [prerelease assets](https://github.com/nisavid/provingkit/releases/tag/preview-8acd0e2af1f4) include each target archive, its complete
root receipt, and its reviewed mode inventory. Use the named target archives;
GitHub’s automatic source archives contain development source.

| Target | Catalog inside its extracted root | Archive SHA-256 |
| --- | --- | --- |
| [agent-plugins](https://github.com/nisavid/provingkit/releases/download/preview-8acd0e2af1f4/provingkit-preview-8acd0e2af1f4-agent-plugins.tar.gz) | `.agents/plugins/marketplace.json` | `a010d4440394179eeedd44692d45e91bb090f2354ea8cc8d837ca31af1e99893` |
| [claude](https://github.com/nisavid/provingkit/releases/download/preview-8acd0e2af1f4/provingkit-preview-8acd0e2af1f4-claude.tar.gz) | `.claude-plugin/marketplace.json` | `e0f6e33d67a1b376418ed3e59f9b2bfb67621a6eeda47c7d57750d110caa2cfa` |
| [cursor](https://github.com/nisavid/provingkit/releases/download/preview-8acd0e2af1f4/provingkit-preview-8acd0e2af1f4-cursor.tar.gz) | `.cursor-plugin/marketplace.json` | `2e546ffc7cd42422031f0fde78678ddbb7604900065952365c00c7a6d3d8edc8` |

Each archive extracts into `provingkit-preview-8acd0e2af1f4-TARGET/`.
Keep that directory intact for local marketplace registration. Catalog entries
resolve to `plugins/PLUGIN_ID` within the target; each plugin is installed as a
whole.

| Target | Qualified artifact SHA-256 | Complete root receipt SHA-256 |
| --- | --- | --- |
| `agent-plugins` | `1edd475db49a10e432e9e4063222155c66b57a2f815a1e3543118eaa5eacdf1f` | `16f6e83d7cedb43f3fb7f81241c5e35eff25e502818f3f4a91841ac1d5c17c34` |
| `claude` | `d59cb439171182459cc904fcace537690634f8d614776ddc15be5262c3b7ee1c` | `3dbcbe98d3fa467c06a2b20ae708cb3c9f597a15567bc91ef9623b1aa41814ca` |
| `cursor` | `6369d531860274882306505ec36b82007f5a2bf40dfcbffe5194662a0bfd99f5` | `f17917d3dbd26fb3265d6cb7d3e4d0b418affe266c1d8ed807486a3368ceba85` |

Verify the downloaded archive against its fixed hash before extraction, then
follow [receipt and mode preservation](../release-artifact-projection.md#receipt-and-mode-preservation).
Preserve the complete receipt bytes and the target mode inventory with the
extracted tree. The release notes bind every asset’s size and SHA-256.

<details>
<summary>Download, extract, and verify the selected target</summary>

Run this from the directory where the verified target should remain. Set
`target` to `agent-plugins`, `claude`, or `cursor`; the default below selects
Agent Plugins/Codex. The commands create a new retained directory, fetch the
target archive with its complete receipt and reviewed mode inventory, and stop
before extraction if any downloaded bytes or archive member shape differ from
this preview.

```sh
set -eu

target=agent-plugins
label=preview-8acd0e2af1f4
source_commit=8acd0e2af1f4508a0e2358d8e01f6a3db7a78ce3
source_tree=1c617b242b5f7962e2567a29117b029a339577b8
asset_base=https://github.com/nisavid/provingkit/releases/download/preview-8acd0e2af1f4/

case "$target" in
  agent-plugins)
    archive_sha=a010d4440394179eeedd44692d45e91bb090f2354ea8cc8d837ca31af1e99893
    receipt_sha=16f6e83d7cedb43f3fb7f81241c5e35eff25e502818f3f4a91841ac1d5c17c34
    modes_sha=9b530b9ae4223815cf688829eedf562c7aa6f0d30b73664a02a47cec411b5fd4
    artifact_sha=1edd475db49a10e432e9e4063222155c66b57a2f815a1e3543118eaa5eacdf1f
    ;;
  claude)
    archive_sha=e0f6e33d67a1b376418ed3e59f9b2bfb67621a6eeda47c7d57750d110caa2cfa
    receipt_sha=3dbcbe98d3fa467c06a2b20ae708cb3c9f597a15567bc91ef9623b1aa41814ca
    modes_sha=6106e3a9a11620acd6fc586de3a7dafa358af6d00cfada4ac7ee253c2f8a780b
    artifact_sha=d59cb439171182459cc904fcace537690634f8d614776ddc15be5262c3b7ee1c
    ;;
  cursor)
    archive_sha=2e546ffc7cd42422031f0fde78678ddbb7604900065952365c00c7a6d3d8edc8
    receipt_sha=f17917d3dbd26fb3265d6cb7d3e4d0b418affe266c1d8ed807486a3368ceba85
    modes_sha=2fa49bb8d87565337e9abe7ddab00e94f2a1d910ecdb571a6eef70a9fbbd22cb
    artifact_sha=6369d531860274882306505ec36b82007f5a2bf40dfcbffe5194662a0bfd99f5
    ;;
  *)
    printf 'Unsupported target: %s\n' "$target" >&2
    exit 2
    ;;
esac

stem="provingkit-$label-$target"
archive="$stem.tar.gz"
receipt="$stem.RECEIPT.json"
modes="$stem.modes.tsv"
root_name="$stem"
preview_stage=$(mktemp -d -- "$PWD/provingkit-preview-download.XXXXXXXX")

curl --fail --location --show-error --silent --output "$preview_stage/$archive" "$asset_base$archive"
curl --fail --location --show-error --silent --output "$preview_stage/$receipt" "$asset_base$receipt"
curl --fail --location --show-error --silent --output "$preview_stage/$modes" "$asset_base$modes"

(
  cd "$preview_stage"
  printf '%s  %s\n%s  %s\n%s  %s\n' \
    "$archive_sha" "$archive" \
    "$receipt_sha" "$receipt" \
    "$modes_sha" "$modes" |
    sha256sum --check --strict
)

python3 - "$preview_stage/$archive" "$root_name" <<'PY'
import sys
import tarfile

archive, expected_root = sys.argv[1:]
seen = set()
with tarfile.open(archive, "r:gz") as tf:
    members = tf.getmembers()
    if not members:
        raise SystemExit("archive is empty")
    for member in members:
        name = member.name
        parts = name.split("/")
        if (
            name.startswith("/")
            or any(part in ("", ".", "..") for part in parts)
            or parts[0] != expected_root
            or name in seen
        ):
            raise SystemExit(f"unsafe or unexpected archive member path: {name}")
        if member.islnk():
            link_parts = member.linkname.split("/")
            if (member.linkname.startswith("/")
                    or any(part in ("", ".", "..") for part in link_parts)
                    or link_parts[0] != expected_root):
                raise SystemExit(f"unsafe archive hard-link target: {member.linkname}")
        elif not (member.isdir() or member.isfile()):
            raise SystemExit(f"archive member is not a file, directory, or contained hard link: {name}")
        seen.add(name)
    receipt_name = f"{expected_root}/RECEIPT.json"
    if receipt_name not in seen:
        raise SystemExit("archive has no root RECEIPT.json")
PY

preview_root="$preview_stage/$root_name"
test ! -e "$preview_root"
tar --extract --gzip --file "$preview_stage/$archive" \
  --directory "$preview_stage" --no-same-owner --same-permissions

python3 - \
  "$preview_root" "$preview_stage/$receipt" "$preview_stage/$modes" \
  "$target" "$artifact_sha" <<'PY'
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path, PurePosixPath

root, receipt_copy, modes_file = map(Path, sys.argv[1:4])
target, expected_artifact = sys.argv[4:6]
source_commit = "8acd0e2af1f4508a0e2358d8e01f6a3db7a78ce3"
slate = [
    "rolecasting",
    "tricritical",
    "versionkeeping",
    "mergecraft",
    "artifact-customs",
    "proseweaving",
]

def fail(message):
    raise SystemExit(message)

def safe_relative(value):
    path = PurePosixPath(value)
    return (
        value == path.as_posix()
        and not path.is_absolute()
        and value not in ("", ".")
        and ".." not in path.parts
    )

try:
    root_mode = root.lstat().st_mode
except FileNotFoundError:
    fail("extracted artifact root is missing")
if not stat.S_ISDIR(root_mode):
    fail("extracted artifact root is not a directory")

actual = {}
for path in root.rglob("*"):
    mode = path.lstat().st_mode
    rel = path.relative_to(root).as_posix()
    if stat.S_ISDIR(mode):
        continue
    if not stat.S_ISREG(mode):
        fail(f"non-regular file or link in extracted artifact: {rel}")
    actual[rel] = path

root_receipt = root / "RECEIPT.json"
try:
    receipt_mode = root_receipt.lstat().st_mode
except FileNotFoundError:
    fail("root RECEIPT.json is missing")
if not stat.S_ISREG(receipt_mode):
    fail("root RECEIPT.json is not a regular file")
receipt_bytes = root_receipt.read_bytes()
if receipt_bytes != receipt_copy.read_bytes():
    fail("extracted and separately downloaded receipt bytes differ")
try:
    receipt = json.loads(receipt_bytes)
except (UnicodeDecodeError, json.JSONDecodeError) as error:
    fail(f"root receipt is not valid JSON: {error}")

expected_fields = {
    "artifact_sha256", "builder", "files", "plugin_slate",
    "policy_sha256", "schema", "source", "target",
}
if set(receipt) != expected_fields:
    fail("root receipt field set differs from the v1 contract")
if receipt["schema"] != "provingkit-artifact-receipt-v1":
    fail("root receipt schema differs from provingkit-artifact-receipt-v1")
if receipt["builder"] != {
    "name": "provingkit-artifact-projector-v1",
    "revision": source_commit,
}:
    fail("root receipt builder identity differs from the qualified projection")
if receipt["source"] != {
    "channel": "preview",
    "commit": source_commit,
    "preview_label": "preview-8acd0e2af1f4",
    "repository": "https://github.com/nisavid/provingkit",
}:
    fail("root receipt source identity differs from the pinned preview")
if receipt["target"] != target:
    fail("root receipt target differs from the selected target")
if receipt["plugin_slate"] != slate:
    fail("root receipt plugin Slate differs from the qualified six plugins")
if receipt["artifact_sha256"] != expected_artifact:
    fail("root receipt artifact digest differs from the qualified target digest")

inventory = []
framed = bytearray(b"provingkit-tree-v1\0")
for rel in sorted(actual):
    if rel == "RECEIPT.json":
        continue
    data = actual[rel].read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    inventory.append({"path": rel, "sha256": digest})
    name = rel.encode()
    framed.extend(len(name).to_bytes(8, "big"))
    framed.extend(name)
    framed.extend(len(data).to_bytes(8, "big"))
    framed.extend(data)

receipt_inventory = receipt["files"]
if not isinstance(receipt_inventory, list):
    fail("root receipt files field is not a list")
paths = []
for row in receipt_inventory:
    if not isinstance(row, dict) or set(row) != {"path", "sha256"}:
        fail("root receipt contains a malformed inventory row")
    if not isinstance(row["path"], str) or not safe_relative(row["path"]):
        fail("root receipt contains an unsafe inventory path")
    if row["path"] == "RECEIPT.json":
        fail("root receipt incorrectly includes itself in the tree inventory")
    if not isinstance(row["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]):
        fail("root receipt contains a malformed file digest")
    paths.append(row["path"])
if paths != sorted(paths) or len(paths) != len(set(paths)):
    fail("root receipt inventory paths are not unique and sorted")
if receipt_inventory != inventory:
    fail("root receipt inventory differs from extracted file paths or bytes")

actual_artifact = hashlib.sha256(framed).hexdigest()
if actual_artifact != expected_artifact:
    fail("provingkit-tree-v1 digest differs from the qualified target digest")

try:
    mode_text = modes_file.read_text(encoding="utf-8")
except (OSError, UnicodeDecodeError) as error:
    fail(f"reviewed mode inventory is unavailable: {error}")
lines = mode_text.splitlines()
if not lines or lines[0] != "path\tmode\torigin":
    fail("reviewed mode inventory header is invalid")
reviewed_modes = {}
for line in lines[1:]:
    fields = line.split("\t", 2)
    if len(fields) != 3:
        fail("reviewed mode inventory contains a malformed row")
    rel, text_mode, _origin = fields
    if not safe_relative(rel) or rel == "RECEIPT.json":
        fail("reviewed mode inventory contains an unsafe or receipt path")
    if rel in reviewed_modes or not re.fullmatch(r"0[0-7]{3}", text_mode):
        fail("reviewed mode inventory contains a duplicate path or invalid mode")
    reviewed_modes[rel] = int(text_mode, 8)

tree_paths = set(actual) - {"RECEIPT.json"}
if set(reviewed_modes) != tree_paths:
    fail("reviewed mode inventory does not cover exactly the artifact files")
for rel, expected_mode in reviewed_modes.items():
    observed_mode = stat.S_IMODE(actual[rel].lstat().st_mode)
    if observed_mode != expected_mode:
        fail(f"reviewed mode differs after extraction: {rel}")

print(f"verified {target}: {len(inventory)} files, artifact {actual_artifact}")
PY

printf '%s\n' "$preview_root" >"$preview_stage/VERIFIED_ARTIFACT_ROOT"
printf '%s\n' \
  "source_commit=$source_commit" \
  "source_tree=$source_tree" \
  "target=$target" \
  "artifact_sha256=$artifact_sha" \
  "receipt_sha256=$receipt_sha" \
  "mode_manifest_sha256=$modes_sha" \
  "archive_sha256=$archive_sha" \
  >"$preview_stage/VERIFICATION.txt"
printf 'Verified artifact root: %s\nRecord: %s\n' \
  "$preview_root" "$preview_stage/VERIFICATION.txt"
```

Use `$preview_root` in the matching client commands below while this shell is
open. `VERIFIED_ARTIFACT_ROOT` records the same absolute path for a later shell;
keep the entire `preview_stage` directory because it holds both that root and
its verification evidence. Repeating the post-extraction Python check only
reads these files; it does not modify the artifact.

These checks establish that the three selected files match the fixed preview
hashes, that the extracted root matches the complete receipt's v1 path-and-byte
inventory and `provingkit-tree-v1` digest, and that every artifact file has its
separately reviewed mode. That tree digest excludes only the root
`RECEIPT.json` and does not bind modes. The receipt check uses `lstat` and
requires a regular file without following a symbolic link; it deliberately
adds no hard-link or link-count policy.

This is the download path for the pinned unsigned preview. Building another
projection remains in `docs/release-artifact-projection.md`; do not run the
projector as part of client installation. A future signed release also needs
its owning signature and release-policy procedure rather than treating these
unsigned hashes as signatures. These checks do not authenticate custody or
establish signed-release, Task Witness, live-client, or live-host authority.

</details>

## Install the preview

Install the published target for your client. Codex and Claude Code register
the verified extracted directory, `preview_root`. Cursor registers the Git ref
shown in its section. The repository's source `main` is not an installable
artifact; clients do not run the projector.
Every member currently reports version `1.0.0`, so record the full source
commit and target artifact digest as well as the version.

The six plugin IDs are `rolecasting`, `tricritical`, `versionkeeping`,
`mergecraft`, `artifact-customs`, and `proseweaving`. Their marketplace is
`provingkit`.

Before changing an existing installation, save its marketplace source and ref,
installed plugin IDs, installation scopes, and enabled or disabled state. Keep
the previous extracted target if it supplies a local marketplace. Save enough
information to restore the previous installation without consulting the new
preview. If `provingkit` is already registered, use the replacement procedure
below before running an install block.

Keep the verification shell open through the Codex or Claude Code install
block. If continuing in a new shell, set `preview_stage` to the retained
directory and `target` to `agent-plugins` (Codex) or `claude` (Claude Code), then
run `preview_root=$(cat "$preview_stage/VERIFIED_ARTIFACT_ROOT")`.

### Codex

These commands assume an initialized client profile. If `CODEX_HOME` explicitly
selects a new configuration directory, create that directory before registration;
the standalone `0.154.0` client rejects a missing one.

Register the verified extracted Agent Plugins target, then install its six members:

```sh
test "$target" = agent-plugins
codex plugin marketplace add "$preview_root" --json
for plugin in rolecasting tricritical versionkeeping mergecraft artifact-customs proseweaving; do
  codex plugin add "$plugin@provingkit"
done
codex plugin list --marketplace provingkit --json
```

Save `codex plugin marketplace list` and the plugin list before a replacement.
Open a new task after installation or reinstallation so it can load the new
skills and tools. The captured CLI exposes no plugin enable/disable command;
its `--enable` and `--disable` options control Codex features. Record and restore
any plugin enabled-state controls separately in the client surface that exposes
them. The CLI commands above have no installation-scope selector.

Codex documents marketplace refs, plugin installation, and
[reinstallation followed by a new task](https://github.com/openai/codex/blob/main/codex-rs/skills/src/assets/samples/plugin-creator/references/installing-and-updating.md).

### Claude Code

Use the verified extracted Claude target, retaining that
directory for as long as it is registered. This path installs at user scope:

```sh
test "$target" = claude
claude plugin marketplace add "$preview_root" --scope user
for plugin in rolecasting tricritical versionkeeping mergecraft artifact-customs proseweaving; do
  claude plugin install "$plugin@provingkit" --scope user
done
claude plugin list --json
```

For project or local scope, run in the intended project and replace `user` in
both commands with `project` or `local`. Use the same scope for later updates
and removal. Save `claude plugin marketplace list`, `claude plugin list --json`,
and the prior enabled state before replacing an installation. Restart Claude
Code after updating.

Claude documents [local marketplace registration and plugin installation](https://code.claude.com/docs/en/plugin-marketplaces).
Its [Git URL examples](https://code.claude.com/docs/en/discover-plugins) establish
branch and tag fragments; this guide uses the local target without assuming
that a commit-SHA fragment works.

### Cursor

Register the published Cursor target:

```sh
agent plugin marketplace add https://github.com/nisavid/provingkit.git \
  --git-ref 6f7659e11af5b39e5d7f09cdad60a048e49084e7
agent plugin marketplace list
```

Then open **Customize** in Cursor's sidebar, find each of the six Provingkit
plugins, select **Install**, and choose project or user scope. Record that scope
and each plugin's enabled state. Use the plugin manager's controls to manage
installed plugins; marketplace registration alone does not establish that they
are installed or enabled. The CLI TUI's `/plugins` surface is another place to
inspect plugin controls, with its behavior still requiring a runtime check.

The shell CLI lists marketplaces visible to the account and exposes marketplace
management, without an `agent plugin install` command. Cursor documents
[Customize installation](https://cursor.com/docs/plugins) and
[commit-pinned CLI marketplace registration](https://cursor.com/docs/cli/changelog).

## Refresh, replace, or remove

A refresh of a commit-pinned marketplace keeps that selected preview. Moving
to a different preview requires explicitly selecting its target commit or
extracted directory.

| Client | Refresh the selected source | Refresh an installed member |
| --- | --- | --- |
| Codex | Local marketplaces do not support `marketplace upgrade`; adding the same path again is a no-op. | Use removal and reinstallation for a definite replacement, then open a new task. |
| Claude Code | `claude plugin marketplace update provingkit` | `claude plugin update PLUGIN_ID@provingkit --scope user`, using the saved scope, then restart. |
| Cursor | `agent plugin marketplace update provingkit` | Inspect the selected plugins in Customize or the CLI TUI after re-indexing; their installed and enabled states need separate checks. |

Keep the marketplace name in refresh commands so the operation targets
`provingkit`. Codex supports marketplace upgrade for Git sources; the local
source used here rejects it. A Claude plugin update is
[scoped to the selected installation](https://code.claude.com/docs/en/plugins-reference).
These commands alone do not prove which cached bytes a client loaded when two
previews share version `1.0.0`.

To replace or roll back a preview:

1. Save the current source/ref, installed set, scopes, and enabled states. For
   rollback, select the previously saved source/ref and extracted target.
2. Remove the affected installed plugins using the client controls below.
   Preserve Claude plugin data with `--keep-data`.
3. Remove the `provingkit` registration being replaced. If rolling back to a
   saved state with neither installed Provingkit plugins nor a `provingkit`
   registration, stop here. Otherwise, run only the marketplace-registration
   command from the matching client section with the selected source or
   extracted root. During rollback, use the saved prior source/ref or extracted
   target. Keep other marketplaces intact.
4. Reinstall the saved plugin set in its saved scopes, restore enabled states,
   and check in a fresh client session.

| Client | Remove one installed plugin | Remove its marketplace registration |
| --- | --- | --- |
| Codex | `codex plugin remove PLUGIN_ID@provingkit` | `codex plugin marketplace remove provingkit` |
| Claude Code | `claude plugin uninstall PLUGIN_ID@provingkit --scope user --keep-data`, using the saved scope | `claude plugin marketplace remove provingkit`; confirm the selected declaration scope in that version's help before removal. |
| Cursor | Use the installed plugin's controls in Customize or the CLI TUI at its saved scope. | `agent plugin marketplace remove provingkit` for the user registration created for this preview. |

Codex plugin removal also removes that plugin's local cache. Claude uninstall removes the installed registration but retains cached
payloads marked with `.orphaned_at`; reinstalling the same qualified target
removed those markers in the isolated test. The documented `--keep-data` option
preserves persistent plugin data; that data-preservation behavior was not
exercised in the empty test homes. Claude exposes `plugin enable` and `plugin disable`; confirm their
scope options in installed help before restoring a saved disabled state.
Cursor marketplace removal is separate from per-plugin installation controls.
No manual cache-directory deletion is part of this procedure.

## Verification and rollout limits

The command descriptions were checked against Codex CLI `0.154.0`, Claude Code
`2.1.270`, Cursor CLI `2026.09.10-fd3934a`, and the linked documentation.
Isolated CLI tests registered the qualified local targets, installed all six
plugins, compared every installed file and mode, removed the registrations,
and reinstalled the same target. Those tests passed for Codex `0.147.0` and
Claude Code `2.1.270` in empty homes with private host state hidden and network
access denied.

The official standalone Linux Codex `0.154.0` executable also passed the full
isolated lifecycle with all six plugin trees matching before and after
reinstallation. It came from the
[`rust-v0.154.0` release](https://github.com/openai/codex/releases/tag/rust-v0.154.0),
asset `codex-x86_64-unknown-linux-musl.tar.gz` with SHA-256
`d7e18b2597ae8f242f5f31ee9e90deef48dbc9edd634d9868fb6435d08c07f02`.
The extracted executable's SHA-256 was
`3188814c35471432d4123203e0eb38e5bddc60226e3d7ddf0e59e649ea140022`.
That temporary executable was tested; the host's Vite Plus proxy and its
resolution state were not exercised, even if they report the same version.

These exercises used the qualified local artifact bytes. Publication readback
is separate, and the tests did not invoke a plugin, model, hook, or MCP server.
They establish removal and reinstallation of this candidate; they do not
establish replacement or rollback between different candidates that both report
`1.0.0`, persistent plugin-data preservation, or live host behavior.

Repeated Claude installation was a no-op, and updating a member still labeled
`1.0.0` reported `up_to_date`. A same-name marketplace from another directory
was rejected by Codex but replaced Claude's user declaration; a Claude project
declaration of that name took precedence in the test workspace. Inventory every
applicable declaration before replacement, and preserve its scope. The user
installation path above was exercised; other installation scopes remain for
rollout verification.

Rollout must check loaded plugin content after replacement, restoration of
enabled states, and the actual host launcher and configuration. For Cursor,
verify the IDE's Settings, Agents Customize, and a fresh CLI/TUI session
separately; an account-visible marketplace entry does not establish equivalent
behavior across those surfaces. Cursor registration and installation were not
performed in the isolated CLI tests.

## Moving `main` and a future signed release

A moving channel resolves a new source commit, artifact digest, and receipt for
each published update. This pinned preview is the available route described
here; the source repository’s `main` branch is not its runtime artifact. A client
refresh does not run the projector or qualify a new candidate.

Keep the full source, target, artifact, receipt, and installed-state records
when selecting a future signed release. Its signature and release-policy checks
are additional prerequisites; they do not relabel this preview.
[Stable release work](https://github.com/nisavid/provingkit/issues/36#stable-release-prerequisite)
requires signed/verifiable Codiquary equipment separately from this preview.
