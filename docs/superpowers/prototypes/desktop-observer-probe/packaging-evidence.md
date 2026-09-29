# Packaging the disposable Desktop observer

The inspected archive supports a copied candidate that preserves every
unchanged member's bytes and metadata. The current candidate has passed complete
offline archive verification. Loading it in the packaged application remains a
separate, unperformed experiment.

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
| Independent archive reader | `@electron/asar 4.3.0`; `package.json` SHA-256 `360ba58371fc5084bd85d5a16bdc3da2f18653b0fd80ae4c7c56b5c31d142a2a`; `lib/asar.js` SHA-256 `8326b28ef2557554175cf738eb608a2d6c48134c878519a0a0242ce3fa4056cb`; observed build dependency files, with no transitive dependency attestation |

These identities do not identify the Code executor a disposable task will
actually use. The live probe must record the selected executor separately.

## Archive shape

The pristine archive contains 364 file members: 362 packed and two unpacked
native modules, with no link entries. Each member has SHA-256 file and 4 MiB
block hashes. An independent packaging scout validated all member sizes and
hashes, including the unpacked modules; I reproduced that validation. The scout
also used `@electron/asar 4.3.0` to extract both inspected JavaScript chunks and
both native modules with matching hashes.

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

## Builder and current candidate

`archive.mjs` preserves the pristine parsed header tree and entire packed
payload. It appends the changed manager chunk and added CommonJS module, then
redirects only those member descriptors to the appended bytes. It recomputes
their sizes and integrity descriptors while preserving unchanged offsets,
executable flags, directory metadata, and unpacked descriptors.

For serialized UTF-8 header length `J`, let `H = 8 + align4(J)`. The builder
emits the prefix `(4, H, H - 4, J)`, header JSON, zero padding, original payload,
and appended bytes. The old manager bytes remain unreachable payload data.
Unchanged header-relative offsets remain valid when the header's physical
length changes.

The current sidecar bundles exactly `desktop-adapter.mjs`,
`observer-contract.mjs`, and `observer-probe.mjs`. Complete verification covered
all 365 candidate members: the added sidecar, the changed manager, and 363
original members whose descriptors and bytes remained unchanged. Independent
ASAR extraction corroborated every file and block hash. Both the resulting
manager and sidecar passed `node --check`.

The generated `build-receipt.json` is build output tied to the proposed
`candidate.asar`. The published `candidate-build.json` is the retained source
copy used for review and authorization. The receipt is the source of the
candidate, manager, sidecar, pristine, and source-input hashes; mutable hashes
are not duplicated in this prose. These two files must compare byte for byte
before the candidate may be staged or authorized.

A change to a bundled module, manager replacement, archive builder, build
dependency, pristine archive, or another build input named by the receipt makes
the candidate evidence stale. Rebuild that candidate, repeat the complete
archive comparison and both syntax checks, and retain the new generated receipt
before authorization. Changes outside those inputs require their affected
checks and review without implying an archive rebuild. The receipt remains the
source of exact hashes. Archive extraction and JavaScript syntax checking do
not establish that the packaged application loads the candidate.

An earlier comment-only manager fixture and empty sidecar established the
archive transformation before the observer candidate existed. It was never
executed and supplies no evidence about current runtime loading.

## Launcher and operating effects

The inspected launcher selects an executable through `CLAUDE_ELECTRON` and
loads its adjacent `resources/app.asar`. It ignores `CLAUDE_APP_ASAR`. Existing
named-profile maintenance may substitute a profile executable and refresh
resources. A symlink to the installed executable does not establish a separate
runtime tree.

The executable's ELF RPATH is `$ORIGIN`, with a direct dependency on
`libffmpeg.so`. A copied runtime would need the matching libraries, resources,
locales, snapshots, unpacked modules, data files, sandbox ownership and mode,
and any path-specific AppArmor treatment. Copied-runtime sandbox behavior has
not been established, and disabling sandboxing is not an experimental setup
step.

The selected route is temporary exchange of the installed archive while
preserving the installed executable, native assets, launcher, and sandbox
layout. It modifies a package-owned file and therefore requires the later
positive grant. The proposal uses one scheduled window in the current signed-in
profile: one candidate launch and one restored launch, with Desktop shut down
before each archive exchange. Those are two application restarts. A restart can
interrupt existing work, and package upgrade or reinstall can overwrite the
experiment. The package declares no backup-managed files.

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

## Sidecar format and runtime file access

The offline builder uses `esbuild 0.28.2` to bundle the adapter, observer, and
shared contract into one CommonJS sidecar. The current complete candidate has
passed synthetic source checks, archive verification, and manager and sidecar
syntax checks. Those results do not establish runtime loading.

[Electron 44.4.3’s filesystem wrapper](https://github.com/electron/electron/blob/v44.4.3/lib/node/asar-fs-wrapper.ts)
extracts an ASAR member when `open` needs a real file. Its virtual `lstat`
produces synthetic inode and timestamp metadata. Comparing the opened file's
identity with the virtual member's metadata is therefore invalid. The adapter
instead reads the packed member through `readFile`, checks its bounded size and
digest, and verifies the physical archive on both sides of that read. This
behavior is source-backed; the packaged application has not been launched.

## Remaining preparation

The chosen installed-archive route still requires a byte-for-byte comparison
of the generated and published receipts, review of every change after the
recorded build, and a private authorization packet. If a bundled or build input
has changed, the dependency rule above also requires a rebuild and complete
comparison. The packet must bind the published source revision, exact
candidate, launcher and argument-file identities, actual task and Code IDs
allocated after fixture creation, cleanup-manifest location, protected backup,
and one current-profile window with the candidate and restored launches. None
of the archive facts establishes that the modified app loads.

Before importing the archive reader, the builder and independent verifier
check its package name, version, package-JSON hash, entrypoint path, and
entrypoint hash. A different identity is unassessed, not established as
incompatible. The build receipt and archive-verification output record those
same facts and explicitly make no transitive dependency attestation.
