// Offline ASAR bytes only. This module never imports packaged app code.
import { createHash } from 'node:crypto';

export const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const blockSize = 4 * 1024 * 1024;

function integrity(bytes) {
  const blocks = [];
  for (let offset = 0; offset < bytes.length; offset += blockSize)
    blocks.push(sha256(bytes.subarray(offset, offset + blockSize)));
  if (!blocks.length) blocks.push(sha256(Buffer.alloc(0)));
  return { algorithm: 'SHA256', hash: sha256(bytes), blockSize, blocks };
}

export function readHeader(bytes) {
  const headerSize = bytes.readUInt32LE(4);
  const jsonSize = bytes.readUInt32LE(12);
  return { tree: JSON.parse(bytes.subarray(16, 16 + jsonSize).toString('utf8')), payloadAt: 8 + headerSize };
}

export function appendMembers(pristine, { expectedSha256, replacements = {}, additions = {} }) {
  if (sha256(pristine) !== expectedSha256) throw new Error('unassessed archive: pristine hash changed');
  const { tree, payloadAt } = readHeader(pristine);
  const chunks = [pristine.subarray(payloadAt)];
  let offset = chunks[0].length;
  const edits = [...Object.entries(replacements).map(([path, bytes]) => ({ path, bytes, kind: 'replacement' })),
    ...Object.entries(additions).map(([path, bytes]) => ({ path, bytes, kind: 'addition' }))];
  for (const { path, bytes, kind } of edits) {
    const parts = path.split('/');
    const name = parts.pop();
    let directory = tree;
    for (const part of parts) directory = directory.files[part];
    const previous = directory.files[name];
    if (kind === 'replacement' && !previous) throw new Error('replacement member missing');
    if (kind === 'replacement' && (previous.unpacked || previous.files || previous.link !== undefined))
      throw new Error('replacement must name a packed file');
    if (kind === 'addition' && previous) throw new Error('addition member already exists');
    directory.files[name] = { ...previous, size: bytes.length, offset: String(offset), integrity: integrity(bytes) };
    chunks.push(bytes);
    offset += bytes.length;
  }
  const json = Buffer.from(JSON.stringify(tree));
  const headerSize = 8 + Math.ceil(json.length / 4) * 4;
  const header = Buffer.alloc(8 + headerSize);
  [4, headerSize, headerSize - 4, json.length].forEach((value, i) => header.writeUInt32LE(value, i * 4));
  json.copy(header, 16);
  return Buffer.concat([header, ...chunks]);
}
