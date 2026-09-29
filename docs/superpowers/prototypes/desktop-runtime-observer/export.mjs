// Used only with a disposable synthetic directory in this prototype.
import { writeFile, rename, unlink } from 'node:fs/promises';
import { randomUUID } from 'node:crypto';

export async function replaceExport(selectedFile, envelope) {
  if (envelope.compatibility.export.state === 'incompatible') throw new Error('incompatible export dependency');
  const temporary = `${selectedFile}.${randomUUID()}.tmp`;
  try {
    await writeFile(temporary, JSON.stringify(envelope), { flag: 'wx', mode: 0o600 });
    await rename(temporary, selectedFile);
  } finally {
    await unlink(temporary).catch(error => { if (error.code !== 'ENOENT') throw error; });
  }
}
