import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import {
  chmod,
  mkdtemp,
  readFile,
  readdir,
  rm,
  writeFile,
} from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';

import * as adapter from './observer-probe.mjs';
import { canonicalFlatJson } from './test-fixtures.mjs';

const sha256 = bytes =>
  createHash('sha256').update(bytes).digest('hex');

const settle = promise =>
  promise.then(
    value => ({ status: 'fulfilled', value }),
    reason => ({ status: 'rejected', reason }),
  );

async function createFixture(
  t,
  {
    queryFactory,
    arm = true,
    armOverrides = {},
  } = {},
) {
  const runDirectory = await mkdtemp(
    join(tmpdir(), 'desktop-observer-lifecycle-'),
  );

  await chmod(runDirectory, 0o700);
  t.after(() => rm(runDirectory, { recursive: true, force: true }));

  let wallTime = 1000;
  let elapsedTime = 1000;
  const calls = [];
  const advance = milliseconds => {
    wallTime += milliseconds;
    elapsedTime += milliseconds;
  };
  const advanceElapsed = milliseconds => {
    elapsedTime += milliseconds;
  };
  const rewindWall = milliseconds => {
    wallTime -= milliseconds;
  };

  const query = queryFactory?.({
    calls,
    advance,
    advanceElapsed,
    rewindWall,
  }) ?? {
    accountInfo() {
      calls.push('accountInfo');
      return { apiProvider: 'firstParty' };
    },

    getContextUsage() {
      calls.push('getContextUsage');
      return { model: 'synthetic-model' };
    },

    listPermissionRules() {
      calls.push('listPermissionRules');
      return {
        state: {
          rules: [],
          workspaceDirectories: [],
          originalCwd: '/synthetic',
          managedOnly: false,
          errors: [],
        },
      };
    },
  };

  const record = {
    taskId: 'synthetic-task',
    codeSessionId: 'synthetic-session',
    generation: 3,
    query,
    inputStream: {},
    host: {},
  };

  const config = {
    schema: adapter.CONFIG_SCHEMA,
    runDirectory,
    runId: 'synthetic-run',
    targetTaskId: record.taskId,
    targetCodeSessionId: record.codeSessionId,
    getterSetId: adapter.GETTER_SET_ID,
    moduleSha256: 'a'.repeat(64),
    copiedAsarSha256: 'b'.repeat(64),
    setupDeadlineMs: 500,
    pollIntervalMs: 5,
  };

  const probe = await adapter.attachProbe({
    config,
    configSha256: sha256(canonicalFlatJson(config)),
    selectReceiver: taskId =>
      taskId === record.taskId ? record : null,
    approvedHostProjection: adapter.projectApprovedHost,
    processIdentity: {
      pid: 4242,
      processStartTicks: '123456',
      uid: process.getuid(),
      monotonicClockId: 'linux-clock-monotonic.v1',
      linuxBootId: '11111111-2222-4333-8444-555555555555',
    },
    now: () => wallTime,
    monotonicNow: () => elapsedTime,
  });

  const bindingKeys = [
    'runId',
    'configSha256',
    'moduleSha256',
    'copiedAsarSha256',
    'appStartNonce',
    'pid',
    'processStartTicks',
    'targetTaskId',
    'targetCodeSessionId',
    'queryGeneration',
    'getterSetId',
    'monotonicClockId',
    'linuxBootId',
  ];

  const armDocument = {
    schema: adapter.ARM_SCHEMA,
    ...Object.fromEntries(
      bindingKeys.map(key => [key, probe.bootstrap[key]]),
    ),
    maxSamples: 1,
    minIntervalMs: 5000,
    observationWindowMs: 30_000,
    perGetterTimeoutMs: 2000,
    ...armOverrides,
  };

  const armPath = join(runDirectory, 'arm.json');
  const writeArmText = text =>
    writeFile(armPath, text, { flag: 'wx', mode: 0o600 });

  if (arm) {
    await writeArmText(`${canonicalFlatJson(armDocument)}\n`);
    await probe.acceptArm();
  }

  return {
    advance,
    advanceElapsed,
    rewindWall,
    armDocument,
    calls,
    probe,
    runDirectory,
    writeArmText,
  };
}

test('one sample owns getter work and discards a hung result after observation expiry', async t => {
  let releaseAccount;
  let markAccountStarted;

  const accountResult = new Promise(resolve => {
    releaseAccount = resolve;
  });

  const accountStarted = new Promise(resolve => {
    markAccountStarted = resolve;
  });

  const fixture = await createFixture(t, {
    armOverrides: {
      observationWindowMs: 100,
    },
    queryFactory: ({ calls }) => ({
      accountInfo() {
        calls.push('accountInfo');
        markAccountStarted();
        return accountResult;
      },

      getContextUsage() {
        calls.push('getContextUsage');
        return { model: 'must-not-be-read' };
      },

      listPermissionRules() {
        calls.push('listPermissionRules');
        return {
          state: {
            rules: [],
            workspaceDirectories: [],
            originalCwd: '/must-not-be-read',
            managedOnly: false,
            errors: [],
          },
        };
      },
    }),
  });

  const firstOutcome = settle(fixture.probe.sample());
  const overlappingOutcome = settle(fixture.probe.sample());

  await accountStarted;
  fixture.advance(101);
  releaseAccount({ apiProvider: 'late-provider' });

  const [first, overlapping] = await Promise.all([
    firstOutcome,
    overlappingOutcome,
  ]);

  assert.equal(first.status, 'fulfilled');
  assert.equal(first.value.result, 'failed');
  assert.equal(first.value.failureClass, 'limit_exceeded');
  assert.equal(first.value.failureStage, 'accountInfo');

  assert.equal(overlapping.status, 'rejected');
  assert.match(
    String(overlapping.reason?.message),
    /sample already in progress/,
  );

  assert.equal(fixture.probe.state, 'terminal');
  assert.deepEqual(fixture.calls, ['accountInfo']);

  const samplePath = join(
    fixture.runDirectory,
    'sample-000001.json',
  );

  assert.deepEqual(
    JSON.parse(await readFile(samplePath, 'utf8')),
    first.value,
  );

  const files = (await readdir(fixture.runDirectory)).sort();

  await assert.rejects(
    fixture.probe.sample(),
    /probe is not armed/,
  );
  await assert.rejects(
    fixture.probe.sample(),
    /probe is not armed/,
  );

  assert.deepEqual(
    (await readdir(fixture.runDirectory)).sort(),
    files,
  );
  assert.deepEqual(files, [
    'arm.json',
    'bootstrap.json',
    'sample-000001.json',
  ]);
  assert.deepEqual(fixture.calls, ['accountInfo']);
});

test('a near-deadline getter wait is clamped to the remaining observation window', async t => {
  let markContextStarted;
  let releaseContext;

  const contextStarted = new Promise(resolve => {
    markContextStarted = resolve;
  });

  const contextResult = new Promise(resolve => {
    releaseContext = resolve;
  });

  const fixture = await createFixture(t, {
    armOverrides: {
      observationWindowMs: 100,
      perGetterTimeoutMs: 2000,
    },
    queryFactory: ({ calls, advanceElapsed }) => ({
      accountInfo() {
        calls.push('accountInfo');
        advanceElapsed(90);
        return { apiProvider: 'firstParty' };
      },

      getContextUsage() {
        calls.push('getContextUsage');
        markContextStarted();
        return contextResult;
      },

      listPermissionRules() {
        calls.push('listPermissionRules');
        return {
          state: {
            rules: [],
            workspaceDirectories: [],
            originalCwd: '/must-not-be-read',
            managedOnly: false,
            errors: [],
          },
        };
      },
    }),
  });

  const sampleResult = fixture.probe.sample();

  await contextStarted;
  fixture.advanceElapsed(11);

  let waitTimer;
  const raced = await Promise.race([
    sampleResult,
    new Promise(resolve => {
      waitTimer = setTimeout(() => resolve(null), 250);
    }),
  ]);

  clearTimeout(waitTimer);
  releaseContext({ model: 'late-model' });

  if (raced === null) {
    await sampleResult;
    assert.fail(
      'getter wait exceeded the remaining observation window',
    );
  }

  assert.equal(raced.result, 'failed');
  assert.equal(raced.failureClass, 'limit_exceeded');
  assert.equal(
    raced.failureStage,
    'getContextUsageSummary',
  );
  assert.equal(fixture.probe.state, 'terminal');
  assert.deepEqual(fixture.calls, [
    'accountInfo',
    'getContextUsage',
  ]);

  assert.deepEqual(
    JSON.parse(
      await readFile(
        join(fixture.runDirectory, 'sample-000001.json'),
        'utf8',
      ),
    ),
    raced,
  );
});

test('a resolved getter is rejected when monotonic time passed its deadline while timers were starved', async t => {
  const fixture = await createFixture(t, {
    armOverrides: {
      perGetterTimeoutMs: 10,
    },
    queryFactory: ({ calls, advanceElapsed }) => ({
      accountInfo() {
        calls.push('accountInfo');
        advanceElapsed(11);
        return { apiProvider: 'late-provider' };
      },

      getContextUsage() {
        calls.push('getContextUsage');
        return { model: 'must-not-be-read' };
      },

      listPermissionRules() {
        calls.push('listPermissionRules');
        return {
          state: {
            rules: [],
            workspaceDirectories: [],
            originalCwd: '/must-not-be-read',
            managedOnly: false,
            errors: [],
          },
        };
      },
    }),
  });

  const envelope = await fixture.probe.sample();

  assert.equal(envelope.result, 'failed');
  assert.equal(envelope.failureClass, 'timeout');
  assert.equal(envelope.failureStage, 'accountInfo');
  assert.equal(fixture.probe.state, 'terminal');
  assert.deepEqual(fixture.calls, ['accountInfo']);

  assert.deepEqual(
    JSON.parse(
      await readFile(
        join(fixture.runDirectory, 'sample-000001.json'),
        'utf8',
      ),
    ),
    envelope,
  );
});

test('settled getter failures remain named field evidence and do not suppress later getters', async t => {
  const fixture = await createFixture(t, {
    queryFactory: ({ calls }) => ({
      accountInfo() {
        calls.push('accountInfo');
        throw new Error('RAW_GETTER_ERROR_CANARY');
      },

      getContextUsage() {
        calls.push('getContextUsage');
        return { model: 42 };
      },

      listPermissionRules() {
        calls.push('listPermissionRules');
        return {
          state: {
            rules: [],
            workspaceDirectories: [],
            originalCwd: '/synthetic',
            managedOnly: false,
            errors: [],
          },
        };
      },
    }),
  });

  const envelope = await fixture.probe.sample();

  assert.equal(envelope.result, 'partial');
  assert.equal(envelope.failureClass, null);
  assert.equal(envelope.failureStage, null);
  assert.equal(fixture.probe.state, 'terminal');
  assert.deepEqual(fixture.calls, [
    'accountInfo',
    'getContextUsage',
    'listPermissionRules',
  ]);

  const { fields } = envelope.observation;

  assert.deepEqual(
    {
      status: fields.accountInfo.status,
      failureClass: fields.accountInfo.failureClass,
      failureStage: fields.accountInfo.failureStage,
      value: fields.accountInfo.value,
    },
    {
      status: 'unavailable',
      failureClass: 'rejected',
      failureStage: 'accountInfo',
      value: null,
    },
  );

  assert.deepEqual(
    {
      status: fields.getContextUsageSummary.status,
      failureClass:
        fields.getContextUsageSummary.failureClass,
      failureStage:
        fields.getContextUsageSummary.failureStage,
      value: fields.getContextUsageSummary.value,
    },
    {
      status: 'unavailable',
      failureClass: 'shape_invalid',
      failureStage: 'getContextUsageSummary',
      value: null,
    },
  );

  assert.equal(fields.listPermissionRules.status, 'available');
  assert.deepEqual(fields.listPermissionRules.value.rules, []);

  const serialized = await readFile(
    join(fixture.runDirectory, 'sample-000001.json'),
    'utf8',
  );

  assert.equal(serialized.includes('RAW_GETTER_ERROR_CANARY'), false);
});

test('wall-clock rollback cannot extend getter or lifecycle deadlines', async t => {
  const fixture = await createFixture(t, {
    queryFactory: ({ calls, advanceElapsed, rewindWall }) => ({
      accountInfo() {
        calls.push('accountInfo');
        rewindWall(500);
        advanceElapsed(2);
        return { apiProvider: 'firstParty' };
      },
      getContextUsage() {
        calls.push('getContextUsage');
        return { model: 'must-not-be-read' };
      },
      listPermissionRules() {
        calls.push('listPermissionRules');
        return {};
      },
    }),
  });

  const envelope = await fixture.probe.sample();

  assert.equal(envelope.result, 'failed');
  assert.equal(envelope.failureClass, 'shape_invalid');
  assert.equal(envelope.failureStage, 'wallClock');
  assert.deepEqual(fixture.calls, ['accountInfo']);
});

test('arm path, read, and schema faults are terminal', async t => {
  const cases = [
    {
      name: 'missing path',
      prepare: async () => {},
    },
    {
      name: 'unreadable JSON',
      prepare: fixture => fixture.writeArmText('{"schema":'),
    },
    {
      name: 'invalid schema',
      prepare: fixture =>
        fixture.writeArmText(
          `${canonicalFlatJson({
            ...fixture.armDocument,
            schema: 'invalid-schema',
          })}\n`,
        ),
    },
    {
      name: 'noncanonical key order',
      prepare: fixture =>
        fixture.writeArmText(
          `${JSON.stringify(
            Object.fromEntries(
              Object.entries(fixture.armDocument).reverse(),
            ),
          )}\n`,
        ),
    },
    {
      name: 'missing final LF',
      prepare: fixture =>
        fixture.writeArmText(
          canonicalFlatJson(fixture.armDocument),
        ),
    },
    {
      name: 'extra whitespace',
      prepare: fixture =>
        fixture.writeArmText(
          `${canonicalFlatJson(fixture.armDocument)} \n`,
        ),
    },
    {
      name: 'duplicate member',
      prepare: fixture =>
        fixture.writeArmText(
          `${canonicalFlatJson(fixture.armDocument).replace(
            `"schema":"${adapter.ARM_SCHEMA}"`,
            `"schema":"${adapter.ARM_SCHEMA}","schema":"${adapter.ARM_SCHEMA}"`,
          )}\n`,
        ),
    },
  ];

  for (const scenario of cases) {
    await t.test(scenario.name, async t => {
      const fixture = await createFixture(t, { arm: false });

      await scenario.prepare(fixture);

      await assert.rejects(
        fixture.probe.acceptArm(),
        /arm acceptance failed/,
      );

      assert.equal(fixture.probe.state, 'terminal');
      assert.deepEqual(fixture.calls, []);

      await assert.rejects(
        fixture.probe.sample(),
        /probe is not armed/,
      );

      assert.equal(
        (await readdir(fixture.runDirectory)).some(name =>
          name.startsWith('sample-'),
        ),
        false,
      );
      assert.deepEqual(fixture.calls, []);
    });
  }
});
