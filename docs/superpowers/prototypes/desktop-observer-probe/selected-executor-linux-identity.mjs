import { constants } from 'node:fs';
import {
  lstat,
  open,
  readFile,
} from 'node:fs/promises';

import {
  LINUX_BOOT_ID_PATH,
  isValidLinuxBootId,
} from './observer-contract.mjs';
import { readProbeSample } from './read-probe-file.mjs';
import {
  createSelectedLinuxExecutorObserver,
} from './selected-executor-linux-identity-internal.mjs';

async function readLinuxBootId() {
  const linuxBootId = (
    await readFile(LINUX_BOOT_ID_PATH, 'utf8')
  ).trim();

  if (!isValidLinuxBootId(linuxBootId)) {
    throw new Error('invalid Linux boot identity');
  }

  return linuxBootId;
}

// Retained experimental source for one separately authorized observation.
// Importing this module performs no reads. Configuration, source presence,
// and an eligible sample never authorize calling this entrypoint.
const observeLiveSelectedLinuxExecutor =
  createSelectedLinuxExecutorObserver({
    processRoot: '/proc',
    readProbeSample,
    lstat,
    open,
    constants,
    getuid: () => process.getuid(),
    now: () => Date.now(),
    monotonicNow: () =>
      Number(process.hrtime.bigint() / 1_000_000n),
    readLinuxBootId,
  });

export async function observeSelectedLinuxExecutor(input) {
  return observeLiveSelectedLinuxExecutor(input);
}
