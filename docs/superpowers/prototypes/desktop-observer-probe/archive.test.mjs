import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, readFile, rm, cp } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createHash } from 'node:crypto';
import { appendMembers } from './archive.mjs';

// The caller supplies an independently installed @electron/asar 4.3.0 reader.
const asar = await import(process.env.PROBE_ASAR_READER);
const sha = bytes => createHash('sha256').update(bytes).digest('hex');

test('a copied archive changes only selected members and remains readable by Electron tooling', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'observer-archive-'));
  try {
    const tree = join(directory, 'tree');
    await mkdir(join(tree, 'nested'), { recursive: true });
    await writeFile(join(tree, 'keep.txt'), 'unchanged');
    await writeFile(join(tree, 'nested', 'manager.js'), 'old manager');
    const pristinePath = join(directory, 'pristine.asar');
    await asar.createPackage(tree, pristinePath);
    const pristine = await readFile(pristinePath);
    const candidate = appendMembers(pristine, {
      expectedSha256: sha(pristine),
      replacements: { 'nested/manager.js': Buffer.from('new manager') },
      additions: { 'nested/observer.js': Buffer.from('observer') },
    });
    const candidatePath = join(directory, 'candidate.asar');
    await writeFile(candidatePath, candidate, { flag: 'wx' });
    assert.equal(asar.extractFile(candidatePath, 'keep.txt').toString(), 'unchanged');
    assert.equal(asar.extractFile(candidatePath, 'nested/manager.js').toString(), 'new manager');
    assert.equal(asar.extractFile(candidatePath, 'nested/observer.js').toString(), 'observer');
    const before = asar.getRawHeader(pristinePath).header;
    const after = asar.getRawHeader(candidatePath).header;
    assert.deepEqual(after.files['keep.txt'], before.files['keep.txt']);
    assert.equal(asar.extractFile(pristinePath, 'nested/manager.js').toString(), 'old manager');
  } finally { await rm(directory, { recursive: true, force: true }); }
});

test('unpacked native assets are preserved and cannot be silently changed into packed members', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'observer-archive-'));
  try {
    const tree = join(directory, 'tree');
    await mkdir(tree);
    await writeFile(join(tree, 'manager.js'), 'old manager');
    await writeFile(join(tree, 'binding.node'), 'synthetic native asset');
    const pristinePath = join(directory, 'pristine.asar');
    await asar.createPackageWithOptions(tree, pristinePath, { unpack: '*.node' });
    const pristine = await readFile(pristinePath);
    const options = { expectedSha256: sha(pristine), replacements: { 'manager.js': Buffer.from('new manager') } };
    const candidatePath = join(directory, 'candidate.asar');
    await writeFile(candidatePath, appendMembers(pristine, options));
    await cp(`${pristinePath}.unpacked`, `${candidatePath}.unpacked`, { recursive: true });
    assert.equal(asar.extractFile(candidatePath, 'binding.node').toString(), 'synthetic native asset');
    assert.deepEqual(asar.getRawHeader(candidatePath).header.files['binding.node'],
      asar.getRawHeader(pristinePath).header.files['binding.node']);
    assert.throws(() => appendMembers(pristine, { ...options,
      replacements: { 'binding.node': Buffer.from('different') } }), /packed file/);
  } finally { await rm(directory, { recursive: true, force: true }); }
});

test('the builder rejects source drift and mistaken replacement or addition names', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'observer-archive-'));
  try {
    const tree = join(directory, 'tree');
    await mkdir(tree);
    await writeFile(join(tree, 'known.js'), 'original');
    const archive = join(directory, 'pristine.asar');
    await asar.createPackage(tree, archive);
    const pristine = await readFile(archive);
    assert.throws(() => appendMembers(pristine, { expectedSha256: '0'.repeat(64) }), /unassessed/);
    assert.throws(() => appendMembers(pristine, { expectedSha256: sha(pristine),
      replacements: { 'missing.js': Buffer.from('replacement') } }), /replacement/);
    assert.throws(() => appendMembers(pristine, { expectedSha256: sha(pristine),
      additions: { 'known.js': Buffer.from('addition') } }), /addition/);
  } finally { await rm(directory, { recursive: true, force: true }); }
});
