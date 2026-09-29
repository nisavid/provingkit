// Independent @electron/asar extraction of the complete candidate, never app execution.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { sha256 } from './archive.mjs';

const [pristinePath, candidatePath, modulePath, managerPath] = process.argv.slice(2);
if (!pristinePath || !candidatePath || !modulePath || !managerPath || !process.env.PROBE_ASAR_READER)
  throw new Error('Supply pristine archive, candidate archive, module, patched manager, and PROBE_ASAR_READER URL.');
const asar = await import(process.env.PROBE_ASAR_READER);
const manager = '.vite/build/index.chunk-B9SZqsi8.js';
const added = '.vite/build/desktopRuntimeObserver.js';
const pristine = await readFile(pristinePath);
assert.equal(sha256(pristine), '4ac2b896dabf3e871f9cf6d9833d02f9f6ad2a839dae6658edc84bb08341238a',
  'Changed input is unassessed; inspect its relevant dependencies before building.');

function files(tree, prefix = '') {
  return Object.entries(tree.files).flatMap(([name, entry]) => entry.files
    ? files(entry, `${prefix}${name}/`) : [[`${prefix}${name}`, entry]]);
}
function verifyIntegrity(bytes, descriptor) {
  assert.equal(bytes.length, descriptor.size);
  assert.equal(descriptor.integrity.algorithm, 'SHA256');
  assert.equal(sha256(bytes), descriptor.integrity.hash);
  const size = descriptor.integrity.blockSize;
  assert.ok(Number.isSafeInteger(size) && size > 0);
  const blocks = [];
  for (let offset = 0; offset < bytes.length; offset += size)
    blocks.push(sha256(bytes.subarray(offset, offset + size)));
  if (!blocks.length) blocks.push(sha256(Buffer.alloc(0)));
  assert.deepEqual(blocks, descriptor.integrity.blocks);
}

const beforeTree = asar.getRawHeader(pristinePath).header;
const afterTree = asar.getRawHeader(candidatePath).header;
const before = new Map(files(beforeTree));
const after = new Map(files(afterTree));
assert.deepEqual([...after.keys()].sort(), [...before.keys(), added].sort());
const expectedTree = structuredClone(beforeTree);
const build = expectedTree.files['.vite'].files.build.files;
build['index.chunk-B9SZqsi8.js'] = after.get(manager);
build['desktopRuntimeObserver.js'] = after.get(added);
assert.deepEqual(afterTree, expectedTree, 'Unexpected directory or member metadata changed');
const changes = [];
for (const [name, descriptor] of after) {
  const bytes = asar.extractFile(candidatePath, name);
  verifyIntegrity(bytes, descriptor);
  if (name === added) {
    assert.deepEqual(bytes, await readFile(modulePath));
    changes.push({ member: name, sha256: sha256(bytes), change: 'added' });
  } else {
    const original = asar.extractFile(pristinePath, name);
    verifyIntegrity(original, before.get(name));
    if (name === manager) {
      assert.notDeepEqual(bytes, original);
      assert.deepEqual(bytes, await readFile(managerPath));
      const metadata = item => Object.fromEntries(Object.entries(item)
        .filter(([key]) => !['size', 'offset', 'integrity'].includes(key)));
      assert.deepEqual(metadata(descriptor), metadata(before.get(name)));
      changes.push({ member: name, sha256: sha256(bytes), change: 'modified' });
    } else {
      assert.deepEqual(descriptor, before.get(name), `Unexpected descriptor change: ${name}`);
      assert.deepEqual(bytes, original, `Unexpected member change: ${name}`);
    }
  }
}
console.log(JSON.stringify({ archiveSha256: sha256(await readFile(candidatePath)),
  originalMembers: before.size, candidateMembers: after.size, changes,
  unchangedMembers: before.size - 1, runtimeLoading: 'unverified' }, null, 2));
