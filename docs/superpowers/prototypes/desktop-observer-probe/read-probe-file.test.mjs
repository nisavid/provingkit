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

import { UNKNOWN_CLAIMS } from './observer-contract.mjs';
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
  monotonicClockId: 'linux-clock-monotonic.v1',
  linuxBootId: '11111111-2222-4333-8444-555555555555',
};

const failedSample = sequence => JSON.stringify({
  schema: 'desktop-observer.sample.v1',
  sequence,
  observedAt: 1_000,
  observedAtMonotonicMs: 5_000,
  state: 'unqualified',
  binding,
  result: 'failed',
  failureClass: 'rejected',
  failureStage: 'accountInfo',
  observation: null,
});

const unavailableField = (
  source,
  freshness,
  failureStage,
) => ({
  source,
  freshness,
  startedAt: 1_000,
  endedAt: 1_000,
  status: 'unavailable',
  failureClass: 'rejected',
  failureStage,
  value: null,
});

const usableSample = sequence => JSON.stringify({
  schema: 'desktop-observer.sample.v1',
  sequence,
  observedAt: 1_000,
  observedAtMonotonicMs: 5_000,
  state: 'unqualified',
  binding,
  result: 'partial',
  failureClass: null,
  failureStage: null,
  observation: {
    collection: {
      startedAt: 1_000,
      endedAt: 1_000,
      startedAtMonotonicMs: 5_000,
      endedAtMonotonicMs: 5_000,
      hostChangedDuringRead: null,
    },
    fields: {
      accountInfo: unavailableField(
        'Query.accountInfo',
        'initialization-cache',
        'accountInfo',
      ),
      getContextUsageSummary: unavailableField(
        'Query.getContextUsage(summary)',
        'query-report; freshness unproven',
        'getContextUsageSummary',
      ),
      listPermissionRules: unavailableField(
        'Query.listPermissionRules',
        'query-report; permission coverage partial',
        'listPermissionRules',
      ),
      hostBefore: unavailableField(
        'Desktop manager projection',
        'manager-snapshot; spawn and event values are retained',
        'hostBefore',
      ),
      hostAfter: unavailableField(
        'Desktop manager projection',
        'manager-snapshot; spawn and event values are retained',
        'hostAfter',
      ),
    },
    unknowns: UNKNOWN_CLAIMS,
  },
});

const unavailable = {
  state: 'unknown',
  reason: 'sample-unavailable',
  qualification: 'unqualified',
};

const invalidSample = {
  state: 'unknown',
  reason: 'invalid-sample',
  qualification: 'unqualified',
};

async function readSyntheticSelectedSample(
  envelopeSequence,
  afterSequence,
  serialized = usableSample(envelopeSequence),
) {
  const runDirectory = await mkdtemp(
    path.join(tmpdir(), 'read-probe-file-sequence-'),
  );
  await chmod(runDirectory, 0o700);

  const selected = path.join(
    runDirectory,
    'sample-000002.json',
  );

  try {
    await writeFile(selected, serialized, {
      mode: 0o600,
    });
    await chmod(selected, 0o600);

    return await readProbeSample({
      runDirectory,
      sequence: 2,
      expectedBinding: binding,
      now: 2_000,
      afterSequence,
      monotonicNow: 6_000,
      monotonicClockId: binding.monotonicClockId,
      linuxBootId: binding.linuxBootId,
      maximumAgeMs: 1_000,
    });
  } finally {
    await rm(runDirectory, {
      recursive: true,
      force: true,
    });
  }
}

test('returns a usable sample when its sequence matches the selected filename', async () => {
  const result = await readSyntheticSelectedSample(2, 1);

  assert.equal(result.state, 'usable-partial');
  assert.equal(result.sample.sequence, 2);
});

test('rejects a usable sample with a higher sequence than the selected filename', async () => {
  assert.deepEqual(
    await readSyntheticSelectedSample(3, 1),
    invalidSample,
  );
});

test('rejects a usable sample with a lower sequence than the selected filename', async () => {
  assert.deepEqual(
    await readSyntheticSelectedSample(1, 0),
    invalidSample,
  );
});

test('returns an incomplete sample when a failed envelope matches the selected filename', async () => {
  assert.deepEqual(
    await readSyntheticSelectedSample(
      2,
      1,
      failedSample(2),
    ),
    {
      state: 'unknown',
      reason: 'incomplete-sample',
      qualification: 'unqualified',
    },
  );
});

test('rejects a failed envelope with a higher sequence than the selected filename', async () => {
  assert.deepEqual(
    await readSyntheticSelectedSample(
      3,
      1,
      failedSample(3),
    ),
    invalidSample,
  );
});

test('rejects a failed envelope with a lower sequence than the selected filename', async () => {
  assert.deepEqual(
    await readSyntheticSelectedSample(
      1,
      0,
      failedSample(1),
    ),
    invalidSample,
  );
});

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
      monotonicNow: 6_000,
      monotonicClockId: binding.monotonicClockId,
      linuxBootId: binding.linuxBootId,
      maximumAgeMs: 1_000,
    });

  const assertUnavailable = result => {
    assert.deepEqual(result, unavailable);
    assert.equal('sample' in result, false);
    assert.equal('observation' in result, false);
  };

  try {
    await writeFile(first, failedSample(1), { mode: 0o600 });
    await chmod(first, 0o600);

    assert.deepEqual(await read(1), {
      state: 'unknown',
      reason: 'incomplete-sample',
      qualification: 'unqualified',
    });

    await writeFile(second, failedSample(1), { mode: 0o600 });
    await chmod(second, 0o644);
    assertUnavailable(await read(2));

    await rm(second);
    await writeFile(symlinkTarget, failedSample(1), {
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
