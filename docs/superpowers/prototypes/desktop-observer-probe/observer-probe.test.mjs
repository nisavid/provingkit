import assert from 'node:assert/strict';
import { chmod, mkdtemp, readFile, readdir, rm, stat, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';

test('public adapter bootstraps disarmed, accepts an exact arm, and exports one allowlisted unqualified sample', async t => {
  const runDirectory = await mkdtemp(
    join(tmpdir(), 'desktop-observer-probe-'),
  );

  await chmod(runDirectory, 0o700);
  t.after(() => rm(runDirectory, { recursive: true, force: true }));

  assert.deepEqual(await readdir(runDirectory), []);

  const adapter = await import('./observer-probe.mjs');

  assert.deepEqual(
    await readdir(runDirectory),
    [],
    'importing the adapter must not touch the run directory',
  );

  const calls = [];
  const selectorArguments = [];

  const query = {
    async accountInfo() {
      calls.push({ name: 'accountInfo', args: [] });
      return {
        apiProvider: 'firstParty',
        tokenSource: 'initialization-cache',
        credential: 'SECRET_CANARY',
        prompt: 'PROMPT_CANARY',
      };
    },

    async getContextUsage(options) {
      calls.push({ name: 'getContextUsage', args: [options] });
      return {
        model: 'synthetic-model-a',
        transcript: 'TRANSCRIPT_CANARY',
        environment: 'ENV_CANARY',
      };
    },

    async listPermissionRules() {
      calls.push({ name: 'listPermissionRules', args: [] });
      return {
        state: {
          rules: [
            {
              behavior: 'allow',
              source: 'session',
              rule: 'Read(/synthetic/**)',
              editability: 'session',
              notInEffect: true,
              privatePayload: 'RULE_CANARY',
            },
          ],
          workspaceDirectories: [
            {
              path: '/synthetic/workspace',
              source: 'session',
              privatePayload: 'GRANT_CANARY',
            },
          ],
          originalCwd: '/synthetic/original',
          managedOnly: false,
          errors: [
            {
              message: 'RAW_ERROR_CANARY',
              stack: 'STACK_CANARY',
            },
          ],
          arbitrary: 'ARBITRARY_CANARY',
        },
      };
    },
  };

  const record = {
    taskId: 'synthetic-task',
    codeSessionId: 'synthetic-code-session',
    generation: 7,
    query: null,
    inputStream: {},
    host: {
      spawnRoute: {
        accountUuid: 'synthetic-account',
        orgId: 'synthetic-org',
      },
      permissionMode: 'default',
      modeEvent: {
        mode: 'default',
        at: 1234,
        generation: 7,
        privatePayload: 'MODE_EVENT_CANARY',
      },
      harnessCwd: '/synthetic/worktree',
      alwaysAllowedReasons: ['synthetic-session-grant'],
      cuAllowedApps: [
        {
          bundleId: 'synthetic.app',
          grantedAt: 100,
          privatePayload: 'APP_GRANT_CANARY',
        },
      ],
      cuGrantFlags: {
        clipboardRead: false,
        clipboardWrite: true,
        systemKeyCombos: false,
        privateFlag: true,
      },
      effectiveCuAllowedApps: [
        {
          bundleId: 'synthetic.effective.app',
          grantedAt: 101,
        },
      ],
      effectiveCuGrantFlags: {
        clipboardRead: true,
        clipboardWrite: false,
        systemKeyCombos: false,
      },
      sessionPermissionUpdates: [
        {
          type: 'workspace',
          privatePayload: 'UPDATE_CANARY',
        },
      ],
      flagScopeSyncPending: false,
      modeRequestsInFlight: 0,
      prompt: 'HOST_PROMPT_CANARY',
      environment: 'HOST_ENV_CANARY',
    },
  };

  const selectReceiver = taskId => {
    selectorArguments.push(taskId);
    return taskId === record.taskId ? record : null;
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

  const attaching = adapter.attachProbe({
    config,
    selectReceiver,
    approvedHostProjection: adapter.projectApprovedHost,
    processIdentity: {
      pid: 4242,
      processStartTicks: '123456',
      uid: process.getuid(),
      monotonicClockId: 'linux-clock-monotonic.v1',
      linuxBootId: '11111111-2222-4333-8444-555555555555',
    },
  });

  setTimeout(() => {
    record.query = query;
  }, 10);

  const probe = await attaching;

  assert.equal(probe.state, 'disarmed');
  assert.deepEqual(calls, []);
  assert.ok(
    selectorArguments.length >= 1 &&
      selectorArguments.every(taskId => taskId === record.taskId),
    'setup must select only the configured task ID',
  );

  const bootstrapPath = join(runDirectory, 'bootstrap.json');
  const bootstrap = JSON.parse(await readFile(bootstrapPath, 'utf8'));

  assert.deepEqual(bootstrap, probe.bootstrap);
  assert.equal((await stat(bootstrapPath)).mode & 0o7777, 0o600);
  assert.equal(bootstrap.targetTaskId, record.taskId);
  assert.equal(
    bootstrap.targetCodeSessionId,
    record.codeSessionId,
  );
  assert.equal(bootstrap.queryGeneration, record.generation);
  assert.equal(bootstrap.getterSetId, adapter.GETTER_SET_ID);

  const arm = {
    schema: adapter.ARM_SCHEMA,
    runId: bootstrap.runId,
    configSha256: bootstrap.configSha256,
    moduleSha256: bootstrap.moduleSha256,
    copiedAsarSha256: bootstrap.copiedAsarSha256,
    appStartNonce: bootstrap.appStartNonce,
    pid: bootstrap.pid,
    processStartTicks: bootstrap.processStartTicks,
    targetTaskId: bootstrap.targetTaskId,
    targetCodeSessionId: bootstrap.targetCodeSessionId,
    queryGeneration: bootstrap.queryGeneration,
    getterSetId: bootstrap.getterSetId,
    monotonicClockId: bootstrap.monotonicClockId,
    linuxBootId: bootstrap.linuxBootId,
    maxSamples: 1,
    minIntervalMs: 5000,
    observationWindowMs: 30_000,
    perGetterTimeoutMs: 2000,
  };

  await writeFile(
    join(runDirectory, 'arm.json'),
    `${JSON.stringify(arm)}\n`,
    { flag: 'wx', mode: 0o600 },
  );

  await probe.acceptArm();

  assert.equal(probe.state, 'armed');
  assert.deepEqual(calls, []);

  const envelope = await probe.sample();

  assert.equal(probe.state, 'terminal');
  assert.equal(envelope.state, 'unqualified');
  assert.equal(envelope.result, 'partial');
  assert.equal(envelope.failureClass, null);
  assert.equal(envelope.failureStage, null);

  assert.deepEqual(calls, [
    { name: 'accountInfo', args: [] },
    {
      name: 'getContextUsage',
      args: [{ detail: 'summary' }],
    },
    { name: 'listPermissionRules', args: [] },
  ]);

  assert.deepEqual(
    Object.keys(envelope.observation).sort(),
    ['collection', 'fields', 'unknowns'],
  );

  const { collection, fields } = envelope.observation;

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

  assert.equal(collection.hostChangedDuringRead, false);
  assert.equal(collection.startedAt, envelope.observedAt);
  assert.equal(
    collection.startedAtMonotonicMs,
    envelope.observedAtMonotonicMs,
  );

  for (const field of Object.values(fields)) {
    assert.equal(field.status, 'available');
    assert.ok(field.startedAt >= collection.startedAt);
    assert.ok(field.endedAt >= field.startedAt);
    assert.ok(field.endedAt <= collection.endedAt);
  }

  assert.deepEqual(fields.accountInfo.value, {
    cachedProvider: 'firstParty',
    providerSource: 'initialization-cache',
  });
  assert.equal(
    fields.accountInfo.freshness,
    'initialization-cache',
  );
  assert.equal(
    fields.getContextUsageSummary.value,
    'synthetic-model-a',
  );
  assert.equal(
    fields.getContextUsageSummary.freshness,
    'query-report; freshness unproven',
  );
  assert.equal(
    fields.listPermissionRules.freshness,
    'query-report; permission coverage partial',
  );

  assert.deepEqual(fields.listPermissionRules.value.rules, [
    {
      behavior: 'allow',
      source: 'session',
      rule: 'Read(/synthetic/**)',
      editability: 'session',
      notInEffect: true,
    },
  ]);

  assert.deepEqual(
    fields.listPermissionRules.value.workspaceGrants,
    [
    {
      path: '/synthetic/workspace',
      source: 'session',
    },
    ],
  );

  assert.equal(fields.listPermissionRules.value.errorCount, 1);
  assert.deepEqual(fields.hostAfter.value.modeEvent, {
    mode: 'default',
    at: 1234,
    generation: 7,
  });
  assert.deepEqual(fields.hostAfter.value.cuAllowedApps, [
    {
      bundleId: 'synthetic.app',
      grantedAt: 100,
    },
  ]);
  assert.equal(
    fields.hostAfter.value.cwdEventProvenance,
    'unavailable',
  );
  assert.equal(
    fields.hostAfter.value.pendingCoverage,
    'unknown',
  );
  assert.equal(
    fields.hostAfter.freshness,
    'manager-snapshot; spawn and event values are retained',
  );

  const samplePath = join(runDirectory, 'sample-000001.json');
  const exportedText = await readFile(samplePath, 'utf8');
  const exported = JSON.parse(exportedText);

  assert.deepEqual(exported, envelope);
  assert.equal((await stat(samplePath)).mode & 0o7777, 0o600);

  for (const canary of [
    'SECRET_CANARY',
    'PROMPT_CANARY',
    'TRANSCRIPT_CANARY',
    'ENV_CANARY',
    'RULE_CANARY',
    'GRANT_CANARY',
    'RAW_ERROR_CANARY',
    'STACK_CANARY',
    'ARBITRARY_CANARY',
    'MODE_EVENT_CANARY',
    'APP_GRANT_CANARY',
    'UPDATE_CANARY',
    'HOST_PROMPT_CANARY',
    'HOST_ENV_CANARY',
  ]) {
    assert.equal(
      exportedText.includes(canary),
      false,
      `${canary} crossed the public export interface`,
    );
  }
});
