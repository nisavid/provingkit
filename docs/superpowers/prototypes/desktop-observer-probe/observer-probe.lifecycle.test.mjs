import assert from 'node:assert/strict';
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

  let currentTime = 1000;
  const calls = [];
  const advance = milliseconds => {
    currentTime += milliseconds;
  };

  const query = queryFactory?.({ calls, advance }) ?? {
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

  const probe = await adapter.attachProbe({
    config: {
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
    },
    selectReceiver: taskId =>
      taskId === record.taskId ? record : null,
    approvedHostProjection: adapter.projectApprovedHost,
    processIdentity: {
      pid: 4242,
      processStartTicks: '123456',
      uid: process.getuid(),
    },
    now: () => currentTime,
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
    await writeArmText(`${JSON.stringify(armDocument)}\n`);
    await probe.acceptArm();
  }

  return {
    advance,
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

test('a resolved getter is rejected when wall-clock time passed its deadline while timers were starved', async t => {
  const fixture = await createFixture(t, {
    armOverrides: {
      perGetterTimeoutMs: 10,
    },
    queryFactory: ({ calls, advance }) => ({
      accountInfo() {
        calls.push('accountInfo');
        advance(11);
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
          `${JSON.stringify({
            ...fixture.armDocument,
            schema: 'invalid-schema',
          })}\n`,
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
