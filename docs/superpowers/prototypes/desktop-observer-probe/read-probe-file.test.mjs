import assert from 'node:assert/strict';
import {
  chmod,
  link,
  mkdtemp,
  rm,
  symlink,
  writeFile,
} from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { readProbeSample } from './read-probe-file.mjs';

const binding = {
  runId: 'run-1',
  configSha256: 'a'.repeat(64),
  moduleSha256: 'b'.repeat(64),
  copiedAsarSha256: 'c'.repeat(64),
  appStartNonce: 'd'.repeat(64),
  pid: 42,
  processStartTicks: '12345',
  targetTaskId: 'task-1',
  targetCodeSessionId: 'session-1',
  queryGeneration: 1,
  getterSetId:
    'desktop-query.readonly.v1:accountInfo,getContextUsage-summary,listPermissionRules',
};

const failedSample = JSON.stringify({
  schema: 'desktop-observer.sample.v1',
  sequence: 1,
  observedAt: 1_000,
  state: 'unqualified',
  binding,
  result: 'failed',
  failureClass: 'rejected',
  failureStage: 'accountInfo',
  observation: null,
});

const unavailable = {
  state: 'unknown',
  reason: 'sample-unavailable',
  qualification: 'unqualified',
};

test('acquires only a safe explicitly selected sample file', async () => {
  const runDirectory = await mkdtemp(
    path.join(tmpdir(), 'read-probe-file-'),
  );
  await chmod(runDirectory, 0o700);

  const first = path.join(
    runDirectory,
    'sample-000001.json',
  );
  const second = path.join(
    runDirectory,
    'sample-000002.json',
  );
  const symlinkTarget = path.join(
    runDirectory,
    'symlink-target.json',
  );

  const read = sequence =>
    readProbeSample({
      runDirectory,
      sequence,
      expectedBinding: binding,
      now: 2_000,
      afterSequence: 0,
      maximumAgeMs: 1_000,
    });

  const assertUnavailable = result => {
    assert.deepEqual(result, unavailable);
    assert.equal('sample' in result, false);
    assert.equal('observation' in result, false);
  };

  try {
    await writeFile(first, failedSample, { mode: 0o600 });
    await chmod(first, 0o600);

    assert.deepEqual(await read(1), {
      state: 'unknown',
      reason: 'incomplete-sample',
      qualification: 'unqualified',
    });

    await writeFile(second, failedSample, { mode: 0o600 });
    await chmod(second, 0o644);
    assertUnavailable(await read(2));

    await rm(second);
    await writeFile(symlinkTarget, failedSample, {
      mode: 0o600,
    });
    await chmod(symlinkTarget, 0o600);
    await symlink(symlinkTarget, second);
    assertUnavailable(await read(2));

    await rm(second);
    await link(symlinkTarget, second);
    assertUnavailable(await read(2));

    await rm(second);
    await rm(symlinkTarget);
    await writeFile(second, Buffer.alloc(16 * 1024 + 1), {
      mode: 0o600,
    });
    await chmod(second, 0o600);
    assertUnavailable(await read(2));

    assertUnavailable(await read(3));
  } finally {
    await rm(runDirectory, {
      recursive: true,
      force: true,
    });
  }
});
