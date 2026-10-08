import { opendir, open, lstat } from 'node:fs/promises';
import { constants } from 'node:fs';
import { join, isAbsolute } from 'node:path';
import { associateSnapshots, admitFixtureWitness, metadataComplete } from './fixture-association.mjs';

const identity = s => Object.fromEntries(['dev', 'ino', 'size', 'mtimeNs', 'ctimeNs'].map(key => [key, String(s[key])]));
const sameIdentity = (a, b) => Object.keys(a).every(key => a[key] === b?.[key]);

async function readRequest(path) {
  const handle = await open(path, constants.O_RDONLY | constants.O_NOFOLLOW | constants.O_NONBLOCK);
  try {
    if (!(await handle.stat()).isFile()) throw new Error('request_not_regular');
    const buffer = Buffer.alloc(131073);
    let acquired = 0;
    while (acquired < buffer.length) {
      const { bytesRead } = await handle.read(buffer, acquired, buffer.length - acquired, null);
      if (!bytesRead) break;
      acquired += bytesRead;
    }
    if (acquired > 131072) throw new Error('request_overflow');
    return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(buffer.subarray(0, acquired)));
  } finally { await handle.close(); }
}

async function readCandidate(path, name, expectedIdentity) {
  let handle;
  const entry = { name, bytesRead: 0, complete: false, capture: { startedAt: Date.now() } };
  try {
    const pathBefore = await lstat(path, { bigint: true });
    if (!pathBefore.isFile()) return { entry, gap: 'metadata_not_regular' };
    handle = await open(path, constants.O_RDONLY | constants.O_NOFOLLOW | constants.O_NONBLOCK);
    const before = await handle.stat({ bigint: true });
    if (!before.isFile()) return { entry, gap: 'metadata_not_regular' };
    entry.before = identity(before);
    if (!sameIdentity(entry.before, identity(pathBefore)) || (expectedIdentity && !sameIdentity(entry.before, expectedIdentity))) {
      return { entry, gap: 'metadata_changed' };
    }
    const buffer = Buffer.alloc(1048577);
    while (entry.bytesRead < buffer.length) {
      const { bytesRead } = await handle.read(buffer, entry.bytesRead, buffer.length - entry.bytesRead, null);
      if (!bytesRead) { entry.complete = true; break; }
      entry.bytesRead += bytesRead;
    }
    if (entry.bytesRead > 1048576) return { entry, gap: 'metadata_overflow' };
    entry.after = identity(await handle.stat({ bigint: true }));
    const pathAfter = await lstat(path, { bigint: true });
    if (!pathAfter.isFile() || !sameIdentity(entry.before, entry.after) || !sameIdentity(entry.after, identity(pathAfter))) {
      return { entry, gap: 'metadata_changed' };
    }
    try {
      const metadata = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(buffer.subarray(0, entry.bytesRead)));
      if (!metadata || Array.isArray(metadata) || typeof metadata !== 'object') throw new Error('invalid_shape');
      return { entry, metadata };
    } catch { return { entry, gap: 'metadata_invalid' }; }
  } catch { return { entry, gap: 'metadata_unavailable' }; }
  finally { if (handle) await handle.close(); entry.capture.completedAt = Date.now(); }
}

async function main() {
  const startedAt = Date.now();
  const [, , flag, requestPath] = process.argv;
  if (process.argv.length !== 4 || flag !== '--request') throw new Error('invalid_command');
  const request = await readRequest(requestPath);
  if (!request || request.schema !== 1 || !['list', 'associate'].includes(request.operation)
      || typeof request.runId !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$/.test(request.runId)
      || typeof request.directory !== 'string' || !isAbsolute(request.directory)
      || request.directory.length > 4096 || request.directory.includes('\0')) throw new Error('invalid_request');
  if (request.operation === 'associate') {
    if (!Array.isArray(request.candidates) || request.candidates.length < 1 || request.candidates.length > 3) {
      throw new Error('invalid_candidates');
    }
    for (const candidate of request.candidates) {
      if (!candidate || typeof candidate.name !== 'string' || candidate.name.length > 255
          || !/^[A-Za-z0-9][A-Za-z0-9._-]*\.json$/.test(candidate.name)) throw new Error('invalid_candidate_name');
      if (candidate.expectedIdentity !== undefined && (!candidate.expectedIdentity
          || !['dev', 'ino', 'size', 'mtimeNs', 'ctimeNs'].every(key =>
            typeof candidate.expectedIdentity[key] === 'string' && /^[0-9]{1,30}$/.test(candidate.expectedIdentity[key])))) {
        throw new Error('invalid_expected_identity');
      }
    }
    if (new Set(request.candidates.map(x => x.name)).size !== request.candidates.length) throw new Error('duplicate_candidates');
    const snapshots = [], files = [], gaps = admitFixtureWitness(request, Date.now());
    for (const { name, expectedIdentity } of gaps.length ? [] : request.candidates) {
      const result = await readCandidate(join(request.directory, name), name, expectedIdentity);
      files.push(result.entry);
      if (result.gap) { gaps.push(result.gap); break; }
      if (!metadataComplete(result.metadata, request.uiWitness.projectField)) { gaps.push('metadata_incomplete'); break; }
      snapshots.push({ name, metadata: result.metadata });
    }
    const association = gaps.length ? { status: 'unknown', gaps, association: null } : associateSnapshots(request, snapshots, Date.now());
    const sample = (object, keys) => Object.fromEntries(keys.map(key => [key, Number.isSafeInteger(object?.[key]) ? object[key] : null]));
    process.stdout.write(JSON.stringify({ schema: 1, runId: request.runId, ...association,
      qualification: 'unqualified', activeDirectory: 'unproved', witnessEvidence: 'caller_supplied',
      sources: { ui: sample(request.uiWitness?.capture, ['startedAt', 'finishedAt']),
        stop: sample(request.stopRecord?.capture, ['startedAt', 'completedAt', 'notBefore']),
        selectionRecheckedAt: Number.isSafeInteger(request.uiWitness?.recheckedAt) ? request.uiWitness.recheckedAt : null },
      acquisition: { capture: { startedAt, completedAt: Date.now() }, files } }) + '\n');
    return;
  }
  const entries = [];
  const directory = await opendir(request.directory, { bufferSize: 1 });
  let entriesObserved = 0, overflow = false;
  for await (const entry of directory) {
    entriesObserved++;
    if (entriesObserved > 128) { overflow = true; break; }
    entries.push({ name: entry.name,
      type: entry.isFile() ? 'file' : entry.isDirectory() ? 'directory' : 'other' });
  }
  process.stdout.write(JSON.stringify({ schema: 1, runId: request.runId, status: overflow ? 'unknown' : 'listed',
    qualification: 'unqualified', activeDirectory: 'unproved', entries, gaps: overflow ? ['listing_overflow'] : [],
    acquisition: { capture: { startedAt, completedAt: Date.now() }, listing: { entriesObserved, overflow }, files: [] } }) + '\n');
}
main().catch(() => { process.stderr.write('Metadata command did not complete.\n'); process.exitCode = 1; });
