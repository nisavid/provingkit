# Packaging the disposable Desktop observer

The inspected archive supports a copied candidate that preserves every
unchanged member's bytes and metadata. Loading the candidate is a separate
experiment. This preparation has not started Desktop or touched a live task.

## Inputs and evidence

The accepted observation module and insertion plan are retained at
`be9abcb2714231eb1f10d5586361dc9d15361ca0` in
`docs/superpowers/prototypes/desktop-runtime-observer/`. Its twelve synthetic
tests passed again during this preparation.

Inspection on 2026-09-29 found:

| Artifact | Identity |
| --- | --- |
| Linux package | `claude-desktop-extra 2.9939.4-1` |
| Archive package | `@ant/desktop 2.9939.4` |
| Electron version file | `44.4.3` |
| Pristine `resources/app.asar` | SHA-256 `4ac2b896dabf3e871f9cf6d9833d02f9f6ad2a839dae6658edc84bb08341238a` |
| Launcher | SHA-256 `015f5232d3c2c40f04f5529d44058d3fd0a80cdce0eddf91dc08688f0a8c867e` |
| Electron executable | SHA-256 `d33007e153db6cee9cc8e2aa6ca986914113bf2355783c3a1fb3af46fd4a1b32` |
| Independent archive reader | `@electron/asar 4.3.0` |

These identities do not identify the Code executor a disposable task will
actually use. The Desktop package allows an automatically downloaded executor;
the live probe must record the selected executor separately.

## Archive shape

The archive contains 364 file members: 362 packed and two unpacked native
modules, with no link entries. Each member has SHA-256 file and 4 MiB block
hashes. An independent packaging scout validated all member sizes and hashes,
including the unpacked modules; I reproduced that validation. The scout also
used `@electron/asar 4.3.0` to extract both
inspected JavaScript chunks and both native modules with matching hashes.

The first four little-endian unsigned integers are
`(4, 98156, 98152, 98146)`. JSON starts at byte 16 and has two zero padding
bytes. The packed payload starts at byte 98164 and occupies 54812290 bytes.
Twenty-four entries share identical extents as asset deduplication; the payload
has no gaps. A validator must allow these identical extents.

The local primary reader's `lib/disk.js` reads packed members at
`8 + headerSize + member.offset`. Its `lib/pickle.js` defines UTF-8 string
length and four-byte padding; `lib/integrity.js` defines file/block hashes.
Their respective SHA-256 values are:

- `0d96e7847fbc9092968d1ed184e3eb857d4d32f1834ce3a914c5cd107ec2084a`
- `f20b3962cbe04a7d25edb271304bfff721737e096541b11a11c19ceede9ac4af`
- `6d211b9d3d39fcd4f7a8c681c6ef1d13a01d43a6e275556826748331859b213c`

## Proposed builder

Preserve the pristine parsed header tree and entire packed payload. Append the
changed manager chunk and added CommonJS module, then redirect only those
member descriptors to the appended bytes. Recompute their sizes and integrity
descriptors. Preserve unchanged offsets, executable flags, directory metadata,
and unpacked descriptors.

For serialized UTF-8 header length `J`, let `H = 8 + align4(J)`. Emit the prefix
`(4, H, H - 4, J)`, header JSON, zero padding, original payload, and appended
bytes. The old manager bytes remain unreachable payload data. Unchanged
header-relative offsets remain valid when the header's physical length changes.

The verification contract compares every original member's descriptor and
bytes, allowing only the intended manager change and added module. A separate
read through Electron's ASAR package must corroborate extraction. Neither
archive extraction nor JavaScript syntax checking establishes runtime loading.

`archive.mjs` implements this byte transformation. Its three tests use the
independent `@electron/asar 4.3.0` writer and reader. They passed for readable
changed archives, preserved unpacked assets, rejected source drift, and
rejected mistaken replacement/addition names.

I also applied the transformation to a copy of the full inspected archive,
using an explicitly marked packaging fixture: a comment appended to the manager
and an empty exported module. `verify-archive.mjs` checked all 365 resulting
members through the independent reader, including all file/block hashes,
unchanged header metadata, and unchanged bytes for 363 original members. That
fixture's archive SHA-256 was
`c15d10232532174daf290605d05d18bf5fe3f8d6794e73d562a7e686218d8566`.
It is not an observer candidate and was never executed. Repeat the verification
with the actual patched manager and observer module before source acceptance.

## Launcher and operating effects

The inspected launcher selects an executable through `CLAUDE_ELECTRON` and
loads its adjacent `resources/app.asar`. It ignores `CLAUDE_APP_ASAR`. Existing
named-profile maintenance may substitute a profile executable and refresh
resources. A symlink to the installed executable does not establish a separate
runtime tree.

The executable's ELF RPATH is `$ORIGIN`, with a direct dependency on
`libffmpeg.so`. A copied runtime needs the matching libraries, resources,
locales, snapshots, unpacked modules, and data files. The package also expects a
root-owned mode-4755 `chrome-sandbox` and, where applicable, a path-specific
AppArmor profile. Copied-runtime sandbox behavior requires its own evidence;
disabling sandboxing is not an experimental setup step.

Temporary replacement of the installed archive would preserve the installed
runtime layout but modify a package-owned file and require a Desktop restart.
A restart can interrupt existing work. Package upgrade or reinstall can
overwrite the experiment. The package declares no backup-managed files.

Restoration must first recheck the installed package identity. An intervening
upgrade prevents blindly restoring an older archive. Restore and verify the
appropriate pristine artifact, then check application and disposable-fixture
behavior separately. Restored bytes alone do not establish restored task state.

## Linux archive-loading evidence

[Electron 44.4.3's ASAR documentation](https://github.com/electron/electron/blob/v44.4.3/docs/tutorial/asar-integrity.md)
lists embedded integrity support on macOS and Windows.
The matching [archive implementation](https://github.com/electron/electron/blob/v44.4.3/shell/common/asar/archive.cc)
guards both member-integrity loading and header validation with
`BUILDFLAG(IS_MAC) || BUILDFLAG(IS_WIN)`. Its other-platform implementation of
`HeaderIntegrity()` returns `std::nullopt`.

The inspected executable contains a fuse wire with settings `010011011`.
That setting alone does not establish Linux header enforcement. The matching
upstream implementation supports preparing the copied Linux archive without
changing executable fuses or embedded signatures. This is a source-backed
compatibility expectation; the exact packaged runtime has not been launched
with the candidate.

## Remaining preparation

The probe plan must choose the runtime location and restoration sequence, bind
the actual Code executor, and identify the exact candidate bytes. The archive
facts above do not establish that the modified app loads.
