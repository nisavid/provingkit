import assert from 'node:assert/strict';
import {
  chmod,
  mkdtemp,
  readFile,
  rm,
  writeFile,
} from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';

import {
  ARM_SCHEMA,
  CONFIG_SCHEMA,
  GETTER_SET_ID,
  attachProbe,
  projectApprovedHost,
} from './observer-probe.mjs';
import { inspectProbeSample } from './probe-reader.mjs';

test('a bounded public sample round-trips through the strict reader', async t => {
  const runDirectory = await mkdtemp(join(tmpdir(), 'probe-reader-'));
  await chmod(runDirectory, 0o700);
  t.after(() => rm(runDirectory, { recursive: true, force: true }));

  let clock = 10_000;
  const now = () => clock;
  let monotonicClock = 50_000;
  const monotonicNow = () => monotonicClock++;

  const record = {
    taskId: 'reader-task',
    codeSessionId: 'reader-session',
    generation: 4,
    inputStream: {},
    host: {
      spawnRoute: {
        accountUuid: 'reader-account',
        orgId: 'reader-org',
      },
      permissionMode: 'before-read',
      harnessCwd: '/reader/workspace',
      modeRequestsInFlight: 0,
    },
  };

  record.query = {
    async accountInfo() {
      clock += 2;
      return {
        apiProvider: 'firstParty',
        tokenSource: 'initialization-cache',
      };
    },

    async getContextUsage(options) {
      assert.deepEqual(options, { detail: 'summary' });
      clock += 3;
      record.host.permissionMode = 'after-read';
      return { model: 'reader-model' };
    },

    async listPermissionRules() {
      clock += 4;
      return {
        state: {
          rules: [{
            behavior: 'allow',
            source: 'session',
            rule: 'Read(/reader/**)',
            editability: 'session',
          }],
          workspaceDirectories: [{
            path: '/reader/workspace',
            source: 'session',
          }],
          originalCwd: '/reader/original',
          managedOnly: false,
          errors: [],
        },
      };
    },
  };

  const probe = await attachProbe({
    config: {
      schema: CONFIG_SCHEMA,
      runDirectory,
      runId: 'reader-run',
      targetTaskId: record.taskId,
      targetCodeSessionId: record.codeSessionId,
      getterSetId: GETTER_SET_ID,
      moduleSha256: 'a'.repeat(64),
      copiedAsarSha256: 'b'.repeat(64),
      setupDeadlineMs: 500,
      pollIntervalMs: 5,
    },
    selectReceiver: taskId => taskId === record.taskId ? record : null,
    approvedHostProjection: projectApprovedHost,
    processIdentity: {
      pid: 4242,
      processStartTicks: '123456',
      uid: process.getuid(),
      monotonicClockId: 'linux-clock-monotonic.v1',
      linuxBootId: '11111111-2222-4333-8444-555555555555',
    },
    now,
    monotonicNow,
  });

  const bootstrap = JSON.parse(
    await readFile(join(runDirectory, 'bootstrap.json'), 'utf8'),
  );

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

  const expectedBinding = Object.fromEntries(
    bindingKeys.map(key => [key, bootstrap[key]]),
  );

  await writeFile(
    join(runDirectory, 'arm.json'),
    `${JSON.stringify({
      schema: ARM_SCHEMA,
      ...expectedBinding,
      maxSamples: 1,
      minIntervalMs: 5000,
      observationWindowMs: 30_000,
      perGetterTimeoutMs: 2000,
    })}\n`,
    { flag: 'wx', mode: 0o600 },
  );

  await probe.acceptArm();
  const produced = await probe.sample();
  const serialized = await readFile(
    join(runDirectory, 'sample-000001.json'),
    'utf8',
  );

  const inspectionOptions = overrides => ({
    now: produced.observation.collection.endedAt,
    monotonicNow:
      produced.observation.collection.endedAtMonotonicMs,
    monotonicClockId: expectedBinding.monotonicClockId,
    linuxBootId: expectedBinding.linuxBootId,
    afterSequence: 0,
    maximumAgeMs: 30_000,
    ...overrides,
  });

  const inspected = inspectProbeSample(
    serialized,
    expectedBinding,
    inspectionOptions(),
  );

  assert.equal(inspected.state, 'usable-partial');
  assert.equal(inspected.qualification, 'unqualified');
  assert.deepEqual(inspected.sample, produced);

  const { collection, fields } = inspected.sample.observation;

  assert.equal(collection.hostChangedDuringRead, true);
  assert.equal(
    collection.startedAtMonotonicMs,
    produced.observedAtMonotonicMs,
  );
  assert.ok(collection.endedAtMonotonicMs >= collection.startedAtMonotonicMs);
  assert.equal(
    fields.hostBefore.value.permissionMode,
    'before-read',
  );
  assert.equal(
    fields.hostAfter.value.permissionMode,
    'after-read',
  );

  assert.deepEqual(
    Object.keys(fields).sort(),
    [
      'accountInfo',
      'getContextUsageSummary',
      'hostAfter',
      'hostBefore',
      'listPermissionRules',
    ],
  );

  for (const field of Object.values(fields)) {
    assert.ok(field.startedAt >= collection.startedAt);
    assert.ok(field.endedAt >= field.startedAt);
    assert.ok(field.endedAt <= collection.endedAt);
  }

  assert.equal(
    fields.accountInfo.freshness,
    'initialization-cache',
  );
  assert.equal(
    fields.getContextUsageSummary.freshness,
    'query-report; freshness unproven',
  );
  assert.equal(
    fields.listPermissionRules.freshness,
    'query-report; permission coverage partial',
  );
  assert.equal(
    fields.hostBefore.freshness,
    'manager-snapshot; spawn and event values are retained',
  );

  const unknown = reason => ({
    state: 'unknown',
    reason,
    qualification: 'unqualified',
  });

  assert.deepEqual(
    inspectProbeSample(serialized, expectedBinding, {
      ...inspectionOptions(),
      now: produced.observedAt + 101,
      monotonicNow: produced.observedAtMonotonicMs + 101,
      maximumAgeMs: 100,
    }),
    unknown('expired'),
  );

  assert.deepEqual(
    inspectProbeSample(
      serialized,
      expectedBinding,
      inspectionOptions({ afterSequence: produced.sequence }),
    ),
    unknown('not-newer'),
  );

  assert.deepEqual(
    inspectProbeSample(
      serialized,
      expectedBinding,
      inspectionOptions({
        now: produced.observedAt + 50,
        monotonicNow: produced.observedAtMonotonicMs + 101,
        maximumAgeMs: 100,
      }),
    ),
    unknown('expired'),
  );

  assert.deepEqual(
    inspectProbeSample(
      serialized,
      expectedBinding,
      inspectionOptions({
        linuxBootId: 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee',
      }),
    ),
    unknown('incomparable-clock'),
  );

  assert.deepEqual(
    inspectProbeSample(
      serialized,
      { ...expectedBinding, targetTaskId: 'different-task' },
      inspectionOptions(),
    ),
    unknown('binding-mismatch'),
  );

  assert.deepEqual(
    inspectProbeSample(
      '{',
      expectedBinding,
      inspectionOptions(),
    ),
    unknown('invalid-sample'),
  );

  const withExtraField = JSON.parse(serialized);
  withExtraField.observation.unapproved = true;

  assert.deepEqual(
    inspectProbeSample(
      JSON.stringify(withExtraField),
      expectedBinding,
      inspectionOptions(),
    ),
    unknown('invalid-sample'),
  );

  const duplicateKey = serialized.replace(
    '"schema":',
    '"schema":"duplicate","schema":',
  );

  assert.deepEqual(
    inspectProbeSample(
      duplicateKey,
      expectedBinding,
      inspectionOptions(),
    ),
    unknown('invalid-sample'),
  );

  const failed = {
    ...JSON.parse(serialized),
    result: 'failed',
    failureClass: 'timeout',
    failureStage: 'accountInfo',
    observation: null,
  };

  assert.deepEqual(
    inspectProbeSample(
      JSON.stringify(failed),
      expectedBinding,
      inspectionOptions(),
    ),
    unknown('incomplete-sample'),
  );

  assert.deepEqual(
    inspectProbeSample(
      JSON.stringify({
        ...failed,
        binding: {
          ...failed.binding,
          targetTaskId: 'foreign-task',
        },
      }),
      expectedBinding,
      inspectionOptions({
        now: failed.observedAt,
        monotonicNow: failed.observedAtMonotonicMs,
      }),
    ),
    unknown('binding-mismatch'),
  );

  assert.deepEqual(
    inspectProbeSample(
      JSON.stringify(failed),
      expectedBinding,
      inspectionOptions({
        now: failed.observedAt + 101,
        monotonicNow: failed.observedAtMonotonicMs + 101,
        maximumAgeMs: 100,
      }),
    ),
    unknown('expired'),
  );

  assert.deepEqual(
    inspectProbeSample(
      JSON.stringify(failed),
      expectedBinding,
      inspectionOptions({ now: failed.observedAt - 1 }),
    ),
    unknown('clock-before-observation'),
  );

  assert.deepEqual(
    inspectProbeSample(
      JSON.stringify(failed),
      expectedBinding,
      inspectionOptions({
        now: failed.observedAt,
        monotonicNow: failed.observedAtMonotonicMs,
        afterSequence: failed.sequence,
      }),
    ),
    unknown('not-newer'),
  );
});
