import { constants } from 'node:fs';
import {
  lstat,
  open,
} from 'node:fs/promises';

import { readProbeSample } from './read-probe-file.mjs';
import {
  createSelectedLinuxExecutorObserver,
} from './selected-executor-linux-identity-internal.mjs';

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
  });

export async function observeSelectedLinuxExecutor(input) {
  return observeLiveSelectedLinuxExecutor(input);
}
