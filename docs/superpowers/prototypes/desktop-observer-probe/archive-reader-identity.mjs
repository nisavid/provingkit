import { readFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { sha256 } from './archive.mjs';

const EXPECTED_ARCHIVE_READER = Object.freeze({
  name: '@electron/asar',
  version: '4.3.0',
  packageJsonSha256:
    '360ba58371fc5084bd85d5a16bdc3da2f18653b0fd80ae4c7c56b5c31d142a2a',
  entrypoint: 'lib/asar.js',
  entrypointSha256:
    '8326b28ef2557554175cf738eb608a2d6c48134c878519a0a0242ce3fa4056cb',
  qualification:
    'observed build dependency files; no transitive dependency attestation',
});

function rejectIdentity() {
  throw new Error('unassessed archive reader identity');
}

export async function assessArchiveReaderIdentity(readerUrl) {
  let url;
  let entrypointPath;

  try {
    url = new URL(readerUrl);
    if (
      url.protocol !== 'file:' ||
      url.search.length !== 0 ||
      url.hash.length !== 0
    ) {
      rejectIdentity();
    }
    entrypointPath = fileURLToPath(url);
  } catch {
    rejectIdentity();
  }

  const packageRoot = dirname(dirname(entrypointPath));
  const packageJsonPath = join(packageRoot, 'package.json');

  if (
    entrypointPath !==
    join(packageRoot, ...EXPECTED_ARCHIVE_READER.entrypoint.split('/'))
  ) {
    rejectIdentity();
  }

  let packageJsonBytes;
  let entrypointBytes;

  try {
    [packageJsonBytes, entrypointBytes] = await Promise.all([
      readFile(packageJsonPath),
      readFile(entrypointPath),
    ]);
  } catch {
    rejectIdentity();
  }

  let packageJson;

  try {
    packageJson = JSON.parse(packageJsonBytes);
  } catch {
    rejectIdentity();
  }

  if (
    packageJson.name !== EXPECTED_ARCHIVE_READER.name ||
    packageJson.version !== EXPECTED_ARCHIVE_READER.version ||
    sha256(packageJsonBytes) !==
      EXPECTED_ARCHIVE_READER.packageJsonSha256 ||
    sha256(entrypointBytes) !==
      EXPECTED_ARCHIVE_READER.entrypointSha256
  ) {
    rejectIdentity();
  }

  return { ...EXPECTED_ARCHIVE_READER };
}

export async function loadAssessedArchiveReader(readerUrl) {
  const identity = await assessArchiveReaderIdentity(readerUrl);
  const archiveReader = await import(readerUrl);
  return { archiveReader, identity };
}
