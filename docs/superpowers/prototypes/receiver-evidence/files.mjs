import { open } from 'node:fs/promises';
import { constants } from 'node:fs';
import { inspectRecords } from './reader.mjs';

// Explicit synthetic selections only; no directory lookup or metadata dereferencing.
export async function readSelectedFiles(input, { clock = Date.now, limitBytes = 262144 } = {}) {
  const capture = { startedAt: clock() };
  const acquisition = { files: [], coherence: 'unverified' };
  try {
    if (!Number.isInteger(limitBytes) || limitBytes < 1 || limitBytes > 1048576) {
      throw Object.assign(new Error(), { code: 'invalid_acquisition_limit' });
    }
    const data = [];
    for (const path of [input.metadataPath, input.transcriptPath]) {
      const entry = { path, bytesRead: 0, complete: false };
      acquisition.files.push(entry);
      const handle = await open(path, constants.O_RDONLY | constants.O_NONBLOCK);
      try {
        if (!(await handle.stat()).isFile()) throw Object.assign(new Error(), { code: 'not_regular_file' });
        const bytes = Buffer.alloc(limitBytes + 1);
        while (entry.bytesRead < bytes.length) {
          const { bytesRead } = await handle.read(bytes, entry.bytesRead, bytes.length - entry.bytesRead, null);
          if (!bytesRead) { entry.complete = true; break; }
          entry.bytesRead += bytesRead;
        }
        if (entry.bytesRead > limitBytes) throw Object.assign(new Error(), { code: 'acquisition_limit' });
        data.push(new TextDecoder('utf-8', { fatal: true }).decode(bytes.subarray(0, entry.bytesRead)));
      } finally { await handle.close(); }
    }
    capture.finishedAt = clock();
    return { ...inspectRecords({ ...input, metadata: JSON.parse(data[0]), transcript: data[1],
      capture, now: input.now ?? capture.finishedAt }), acquisition };
  } catch (error) {
    capture.finishedAt = clock();
    return { status: 'unknown', qualification: 'unqualified', compatibility: input.compatibility ?? { status: 'unassessed' },
      notices: [], acknowledgments: [], gaps: ['acquisition_failed'], error: error.code ?? 'invalid_file_data', capture, acquisition };
  }
}
