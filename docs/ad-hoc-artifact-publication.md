# Publish retained ad hoc artifacts

Publish clean artifacts for a pinned source selection through the ordinary
`ivan/provingkit-ad-hoc-artifacts` branch. This gives a fresh machine durable
HTTPS inputs without building plugins during installation or depending on a
prior machine's cache. Each generation carries three archives, three complete
receipts, and three mode inventories.

Use this procedure for an authorized ad hoc selection. Agents use
`capturing-agent-procedures` and record this document's reviewed revision in
the adoption handoff. Use `checkpointing-and-publishing-git-work` for commits,
branch creation, and its reviewed planner/executor. Source qualification,
profile activation, native discovery, and retirement remain with their owners.

## Bind the inputs

Keep these identities distinct:

| Identity | Use |
| --- | --- |
| Product source commit | Full selected Provingkit commit in each receipt and the installation profile's `source.commit`. |
| Transport base commit | Advertised branch tip from which the publication commit descends. It need not equal the product source commit. |
| Publication commit | Full commit containing the nine download files. Pin this commit in every HTTPS URL. |
| Archive, receipt, and mode SHA-256 | Exact downloaded bytes for each target. |
| Artifact tree SHA-256 | `provingkit-tree-v1`, which covers paths and bytes but excludes the root receipt and does not bind modes. |

Start with the owning task's selected, reviewed source commit and its accepted
three target trees. Follow [artifact projection](release-artifact-projection.md)
from that clean, detached source checkout into fresh output directories. For
selected main source, use the supported `--channel main`; the full commit is
still pinned. Do not add an `ad_hoc` projector channel or edit the emitted
`preview_label`. The installation profile's adoption stage is `ad_hoc`.

```sh
set -eu
for target in agent-plugins claude cursor; do
  python "$PROVINGKIT_PRODUCT_SOURCE/scripts/build_release_artifacts.py" \
    --source "$PROVINGKIT_PRODUCT_SOURCE" --channel main --target "$target" \
    --output "$PROVINGKIT_PROJECTION_ROOT/$target"
done
```

Complete the owning source/projection checks before packing. Retain their
source commit/tree, builder and policy identities, each exact root receipt,
artifact digest, file inventory, and reviewed `<target>.modes.tsv` with header
`path<TAB>mode<TAB>origin`. The mode inventory covers every artifact file except
the root receipt; separately record and preserve the receipt's observed mode.
Check copied modes against source Git modes and generated modes against the
projection contract. An observed mode list alone does not qualify source.

Use the complete six-member catalog from one source snapshot when preserving
other installations in the shared marketplace. The profile may select only
Proseweaving, Versionkeeping, and Mergecraft; catalog presence does not select
the other members for installation or update.

## Pack and freeze one generation

The following Linux/Python 3 recipe preserves the reviewed packing convention:
root first, sorted directories, then sorted regular files; GNU tar format;
zero timestamps and owner/group IDs; empty owner/group names; directory mode
`0755`; original file modes; and gzip level 9 without filename or timestamp.
Receipt and mode files are copied as bytes, without JSON or TSV reserialization.

Set `PROVINGKIT_SOURCE_COMMIT` to the full product source commit,
`PROVINGKIT_PROJECTION_ROOT` to the three accepted trees, `PROVINGKIT_MODE_ROOT`
to their reviewed mode files, and `PROVINGKIT_TRANSPORT_STAGE` to a new directory.
Export these variables. Keep the accepted inputs unchanged throughout packing
and readback. Run this block with a shell that stops on failure (`set -eu`).

```sh
python - <<'PY'
import gzip
import os
import re
import shutil
import stat
import tarfile
from pathlib import Path

commit = os.environ["PROVINGKIT_SOURCE_COMMIT"]
if not re.fullmatch(r"[0-9a-f]{40}", commit):
    raise SystemExit("a full product source commit is required")
trees = Path(os.environ["PROVINGKIT_PROJECTION_ROOT"])
modes = Path(os.environ["PROVINGKIT_MODE_ROOT"])
stage = Path(os.environ["PROVINGKIT_TRANSPORT_STAGE"])
stage.mkdir(parents=True, exist_ok=False)
for target in ("agent-plugins", "claude", "cursor"):
    source = trees / target
    if not stat.S_ISDIR(source.lstat().st_mode):
        raise SystemExit("projection root must be a real directory")
    paths = sorted(source.rglob("*"), key=lambda p: p.relative_to(source).as_posix())
    directories, files = [], []
    for path in paths:
        mode = path.lstat().st_mode
        if stat.S_ISDIR(mode):
            directories.append(path)
        elif stat.S_ISREG(mode):
            files.append(path)
        else:
            raise SystemExit(f"non-regular projection member: {path}")
    receipt = source / "RECEIPT.json"
    mode_file = modes / f"{target}.modes.tsv"
    if not all(stat.S_ISREG(p.lstat().st_mode) for p in (receipt, mode_file)):
        raise SystemExit("receipt and mode inventory must be regular files")
    destination = stage / "ad-hoc" / commit / target
    destination.mkdir(parents=True, exist_ok=False)
    root = f"provingkit-ad-hoc-{commit}-{target}"
    with (destination / "artifact.tar.gz").open("xb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w", format=tarfile.GNU_FORMAT) as archive:
                for path in [source, *directories, *files]:
                    relative = path.relative_to(source).as_posix()
                    name = root if path == source else f"{root}/{relative}"
                    is_directory = stat.S_ISDIR(path.lstat().st_mode)
                    member = tarfile.TarInfo(name + ("/" if is_directory else ""))
                    member.uid = member.gid = member.mtime = 0
                    member.uname = member.gname = ""
                    member.mode = 0o755 if is_directory else stat.S_IMODE(path.lstat().st_mode)
                    member.type = tarfile.DIRTYPE if is_directory else tarfile.REGTYPE
                    if is_directory:
                        archive.addfile(member)
                    else:
                        member.size = path.stat().st_size
                        with path.open("rb") as stream:
                            archive.addfile(member, stream)
    shutil.copyfile(receipt, destination / "RECEIPT.json")
    shutil.copyfile(mode_file, destination / "modes.tsv")
PY
```

Run the block again with another fresh staging directory. Compare all nine
files byte for byte, then run the extraction check below against the first
stage before freezing it. Record each file's size and lowercase SHA-256, the
three archive root names, and the accepted tree digests in the adoption handoff.
Keep that record outside the transport generation. Do not repack reviewed
archives during publication. If an existing generation for this source has
different bytes, stop and reconcile the producer or selection before publishing.

## Publish with ordinary branch ancestry

For the first publication, start a persistent task worktree at a freshly
observed advertised `main` tip. Keep its existing tree and add only the nine
files below `ad-hoc/<product-source-commit>/`. Create one task-owned commit.
This normal child commit satisfies Versionkeeping's ancestry contract; an
orphan branch does not. Do not merge the artifact transport branch into `main`.

Use publication request schema 2 with these values:

| Field | First publication | Later generation |
| --- | --- | --- |
| `start_head` | Observed advertised `main` tip | Observed artifact branch tip |
| `source_sha` | Reviewed publication commit | Reviewed publication commit |
| `task_owned_commits` | Exact new publication commit(s) | Exact new publication commit(s) |
| `adopted_commits` / `removal_authorized_commits` | Empty / empty | Empty / empty |
| `explicit_destination` | Remote for `nisavid/provingkit`, full ref `refs/heads/ivan/provingkit-ad-hoc-artifacts` | Same |
| `default_branch_policy` | `null` | `null` |
| `allow_create` / `creation_base_ref` | `true` / `refs/heads/main` | `false` / `null` |

Resolve the planner/executor from the loaded Versionkeeping plugin. The planner
may fetch objects and create temporary refs, so invoke it only in the authorized
publication stage. Review its complete `ready` bytes, retain their SHA-256
separately, execute once, and require terminal `verified` evidence for the
publication commit and destination. A request file alone is not a ready plan.

With `VERSIONKEEPING_ROOT` resolved by the harness and the task's reviewed
request and plan paths selected, the owning commands are:

```sh
python "$VERSIONKEEPING_ROOT/skills/checkpointing-and-publishing-git-work/scripts/plan_git_publication.py" \
  --repo "$PROVINGKIT_TRANSPORT_WORKTREE" --request "$PROVINGKIT_PUBLICATION_REQUEST" \
  > "$PROVINGKIT_PUBLICATION_PLAN"
# Continue only after review of ready plan bytes and separate digest custody.
python "$VERSIONKEEPING_ROOT/skills/checkpointing-and-publishing-git-work/scripts/execute_git_publication.py" \
  --repo "$PROVINGKIT_TRANSPORT_WORKTREE" --plan "$PROVINGKIT_PUBLICATION_PLAN" \
  --reviewed-plan-sha256 "$PROVINGKIT_REVIEWED_PLAN_SHA256"
```

The reviewed digest argument has the form `sha256:<64-lowercase-hex>`.

If the first `main` tip has moved so the start is no longer advertised and the
creation-base ancestry check blocks, prepare the artifact-only change on the
newly observed `main` tip and review the replacement commit and plan. Keep the
product source and all nine artifact bytes unchanged. Stop on conflicting
paths or unexpected remote commits. For later generations, append to the
existing transport branch, preserving every earlier generation and publication
commit. No history rewrite, automatic adoption of other commits, raw-push
fallback, branch deletion, tag, or Release object belongs to this route.

## Read back all nine pinned URLs

Let `S` be the product source commit and `P` the verified publication commit.
The nine immutable URL forms are:

| Target | Archive | Receipt | Modes |
| --- | --- | --- | --- |
| Agent Plugins/Codex | `https://raw.githubusercontent.com/nisavid/provingkit/P/ad-hoc/S/agent-plugins/artifact.tar.gz` | `https://raw.githubusercontent.com/nisavid/provingkit/P/ad-hoc/S/agent-plugins/RECEIPT.json` | `https://raw.githubusercontent.com/nisavid/provingkit/P/ad-hoc/S/agent-plugins/modes.tsv` |
| Claude | `https://raw.githubusercontent.com/nisavid/provingkit/P/ad-hoc/S/claude/artifact.tar.gz` | `https://raw.githubusercontent.com/nisavid/provingkit/P/ad-hoc/S/claude/RECEIPT.json` | `https://raw.githubusercontent.com/nisavid/provingkit/P/ad-hoc/S/claude/modes.tsv` |
| Cursor | `https://raw.githubusercontent.com/nisavid/provingkit/P/ad-hoc/S/cursor/artifact.tar.gz` | `https://raw.githubusercontent.com/nisavid/provingkit/P/ad-hoc/S/cursor/RECEIPT.json` | `https://raw.githubusercontent.com/nisavid/provingkit/P/ad-hoc/S/cursor/modes.tsv` |

Replace both letters with their full commits. Store ordinary Git blobs; Git
LFS pointers are not archive bytes at these URLs. Neither branch names nor
version strings may replace commit and checksum pins.

After publication, set `PROVINGKIT_PUBLICATION_COMMIT` and a new
`PROVINGKIT_READBACK` directory. Download without authentication, keeping failed
downloads and command status for diagnosis. Run with `set -eu`:

```sh
mkdir "$PROVINGKIT_READBACK"
for target in agent-plugins claude cursor; do
  mkdir "$PROVINGKIT_READBACK/$target"
  for name in artifact.tar.gz RECEIPT.json modes.tsv; do
    curl --fail --location --show-error --silent \
      --output "$PROVINGKIT_READBACK/$target/$name" \
      "https://raw.githubusercontent.com/nisavid/provingkit/$PROVINGKIT_PUBLICATION_COMMIT/ad-hoc/$PROVINGKIT_SOURCE_COMMIT/$target/$name"
    cmp "$PROVINGKIT_TRANSPORT_STAGE/ad-hoc/$PROVINGKIT_SOURCE_COMMIT/$target/$name" \
      "$PROVINGKIT_READBACK/$target/$name"
  done
done
```

Compare the hashes and sizes with the separately retained reviewed record.
Require all nine byte comparisons before extraction. Use the following check
with `PROVINGKIT_CHECK_INPUT` set to either the staged `ad-hoc/<S>` directory
before publication or the downloaded readback directory afterward. Set
`PROVINGKIT_EXTRACTED` to a new output directory and export both variables.
The receipt and mode equality checks retain the original accepted inputs as
the comparison source; they never derive new acceptance from a download.

```sh
python - <<'PY'
import csv
import hashlib
import json
import os
import stat
import subprocess
import tarfile
from pathlib import Path

inputs = Path(os.environ["PROVINGKIT_CHECK_INPUT"])
expected = Path(os.environ["PROVINGKIT_PROJECTION_ROOT"])
modes = Path(os.environ["PROVINGKIT_MODE_ROOT"])
commit = os.environ["PROVINGKIT_SOURCE_COMMIT"]
output = Path(os.environ["PROVINGKIT_EXTRACTED"])
output.mkdir(parents=True, exist_ok=False)

def inventory(root):
    if not stat.S_ISDIR(root.lstat().st_mode):
        raise SystemExit("artifact root must be a real directory")
    files = {}
    for path in root.rglob("*"):
        mode = path.lstat().st_mode
        if stat.S_ISDIR(mode):
            continue
        if not stat.S_ISREG(mode):
            raise SystemExit(f"non-regular member: {path}")
        files[path.relative_to(root).as_posix()] = (path.read_bytes(), stat.S_IMODE(mode))
    return files

for target in ("agent-plugins", "claude", "cursor"):
    downloaded = inputs / target
    source = expected / target
    receipt_bytes = (source / "RECEIPT.json").read_bytes()
    if (downloaded / "RECEIPT.json").read_bytes() != receipt_bytes:
        raise SystemExit("companion receipt bytes differ")
    if (downloaded / "modes.tsv").read_bytes() != (modes / f"{target}.modes.tsv").read_bytes():
        raise SystemExit("companion mode bytes differ")
    root_name = f"provingkit-ad-hoc-{commit}-{target}"
    with tarfile.open(downloaded / "artifact.tar.gz", "r:gz") as archive:
        members = archive.getmembers()
    seen = set()
    for member in members:
        parts = member.name.split("/")
        if parts[0] != root_name or any(part in ("", ".", "..") for part in parts) or member.name in seen:
            raise SystemExit("unexpected archive member path")
        if not (member.isdir() or member.isfile()):
            raise SystemExit("archive contains a link or special member")
        seen.add(member.name)
    if not members or not members[0].isdir() or members[0].name != root_name:
        raise SystemExit("archive must begin with its single root directory")
    subprocess.run(["tar", "--extract", "--gzip", "--file", str(downloaded / "artifact.tar.gz"),
                    "--directory", str(output), "--no-same-owner", "--same-permissions"], check=True)
    root = output / root_name
    actual = inventory(root)
    if actual != inventory(source):
        raise SystemExit("extracted file inventory, bytes, or modes differ")
    receipt = json.loads(receipt_bytes)
    if receipt["source"]["commit"] != commit or receipt["target"] != target:
        raise SystemExit("receipt source or target differs")
    framed = bytearray(b"provingkit-tree-v1\0")
    rows = []
    for relative, (data, mode) in sorted(actual.items()):
        if relative == "RECEIPT.json":
            continue
        name = relative.encode("utf-8")
        framed += len(name).to_bytes(8, "big") + name + len(data).to_bytes(8, "big") + data
        rows.append({"path": relative, "sha256": hashlib.sha256(data).hexdigest()})
    if rows != receipt["files"] or hashlib.sha256(framed).hexdigest() != receipt["artifact_sha256"]:
        raise SystemExit("receipt inventory or tree digest differs")
    with (downloaded / "modes.tsv").open(newline="", encoding="utf-8") as stream:
        mode_rows = list(csv.DictReader(stream, delimiter="\t"))
    recorded = {row["path"]: int(row["mode"], 8) for row in mode_rows}
    if len(recorded) != len(mode_rows) or recorded != {name: mode for name, (_, mode) in actual.items() if name != "RECEIPT.json"}:
        raise SystemExit("mode inventory differs")
    print(f"verified {target}: {len(rows)} files; exact receipt, bytes, and modes")
PY
```

Record the nine final URLs and hashes only after public readback passes. The
dotfiles profile uses the existing archive/receipt/mode download fields and
one-component stripping. Its `source.commit` remains `S`, while URLs contain
`P`; no installer or acquisition mechanism changes. Return the public adoption
record, source/transport identities, exact nine-file record, public readback
results, and retained recovery references to the installation owner. Failed or
incomplete publication/readback is not a usable new profile.

## Retain supported generations

Keep the transport branch and every published generation by default. Append
without rewriting history so every pinned publication commit stays reachable.
Do not remove a generation, branch, or necessary commit while a supported
selection or retained recovery profile refers to it. Task and host cleanup do
not authorize remote artifact cleanup. Retirement requires explicit owner
disposition of those references and preservation of the agreed recovery inputs.

Digest pins detect changed bytes; retained remote generations provide retrieval.
Neither guarantees GitHub availability. A later mirror needs its own reviewed
URLs and byte readback. Ordinary Git storage is simple for these small files,
but compressed archives grow repository history with each generation. Measure
the nine-file total before publication and revisit storage with the owner if
growth becomes material; do not quietly switch to expiring workflow artifacts
or Git LFS. This route leaves preview assets, release tags, and release policy
unchanged.
