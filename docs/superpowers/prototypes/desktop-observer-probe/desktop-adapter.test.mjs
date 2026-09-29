import assert from 'node:assert/strict';
import {
  chmod,
  mkdtemp,
  rm,
  writeFile,
} from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';

import {
  ARM_SCHEMA,
  GETTER_SET_ID,
  attachProbe,
  projectApprovedHost,
} from './observer-probe.mjs';
import {
  createDesktopAdapter,
  noteCodeSessionId,
  noteQueryInstalled,
  recordModeEvent,
  teardownQuery,
} from './desktop-adapter.mjs';

test('selected Desktop receiver remains guarded until arm and invalidates on record replacement', async () => {
  const root = await mkdtemp(join(tmpdir(), 'desktop-adapter-'));
  const runDirectory = join(root, 'run');

  await chmod(root, 0o700);
  await import('node:fs/promises').then(({ mkdir }) =>
    mkdir(runDirectory, { mode: 0o700 }),
  );

  try {
    const queryCalls = [];
    const query = {
      async accountInfo() {
        queryCalls.push('accountInfo');
        return {
          apiProvider: 'firstParty',
          tokenSource: 'fixture',
        };
      },
      async getContextUsage() {
        queryCalls.push('getContextUsage');
        return {
          model: 'fixture-model-a',
          unrelated: 'omit me',
        };
      },
      async listPermissionRules() {
        queryCalls.push('listPermissionRules');
        return {
          state: {
            rules: [{
              behavior: 'allow',
              source: 'session',
              rule: 'Read(/fixture/**)',
              editability: 'session',
            }],
            workspaceDirectories: [{
              path: '/fixture',
              source: 'session',
            }],
            originalCwd: '/fixture/original',
            managedOnly: false,
          },
        };
      },
    };

    let rawRecord = {
      sessionId: 'fixture-task',
      cliSessionId: 'fixture-code-a',
      cliPid: 4321,
      cliPidAtMs: 1200,
      cliReportedVersion: 'fixture-version',
      query,
      inputStream: {},
      permissionMode: 'default',
      harnessCwd: '/fixture/worktree',
      alwaysAllowedReasons: new Set(),
      cuAllowedApps: [],
      cuGrantFlags: {
        clipboardRead: false,
        clipboardWrite: false,
        systemKeyCombos: false,
      },
      effectiveCuAllowedApps: [],
      effectiveCuGrantFlags: {
        clipboardRead: false,
        clipboardWrite: false,
        systemKeyCombos: false,
      },
      sessionPermissionUpdates: [],
      flagScopeSyncPending: false,
      permissionModeRequestsInFlight: {
        query,
        count: 0,
      },
    };

    const getCalls = [];
    const sessions = {
      get(taskId) {
        getCalls.push(taskId);
        return taskId === rawRecord.sessionId ? rawRecord : undefined;
      },
      values() {
        throw new Error('record enumeration is forbidden');
      },
      [Symbol.iterator]() {
        throw new Error('record enumeration is forbidden');
      },
    };

    let unavailableChecks = 0;
    const manager = {
      sessions,
      cliOAuthTokenKeeper: {
        spawnAccountOf(record) {
          assert.equal(record, rawRecord);
          return {
            accountUuid: 'fixture-account',
            orgId: 'fixture-org',
          };
        },
      },
    };

    const adapter = createDesktopAdapter({
      manager,
      targetTaskId: 'fixture-task',
      isUnavailable(record) {
        unavailableChecks += 1;
        assert.equal(record, rawRecord);
        return false;
      },
      effectiveCuAllowedApps: record =>
        record.effectiveCuAllowedApps,
      effectiveCuGrantFlags: record =>
        record.effectiveCuGrantFlags,
      now: () => 1234,
    });

    assert.equal(adapter.selectReceiver('not-target'), null);
    assert.deepEqual(getCalls, []);

    const firstView = adapter.selectReceiver('fixture-task');
    assert.equal(
      adapter.selectReceiver('fixture-task'),
      firstView,
    );

    assert.equal(
      noteQueryInstalled(manager, 'fixture-task', query),
      true,
    );
    assert.equal(teardownQuery(manager, rawRecord), true);

    assert.equal(
      noteCodeSessionId(manager, rawRecord, 'fixture-code-b'),
      true,
    );
    rawRecord.cliSessionId = 'fixture-code-b';

    assert.equal(
      noteCodeSessionId(manager, rawRecord, 'fixture-code-a'),
      true,
    );
    rawRecord.cliSessionId = 'fixture-code-a';

    assert.equal(firstView.generation, 5);
    assert.equal(
      recordModeEvent(manager, rawRecord, {}, 'ignored'),
      false,
    );
    assert.equal(
      recordModeEvent(manager, rawRecord, query, 'default'),
      true,
    );
    assert.deepEqual(firstView.host.modeEvent, {
      mode: 'default',
      at: 1234,
      generation: 5,
    });

    const config = {
      schema: 'desktop-observer.probe-config.v1',
      runDirectory,
      runId: 'fixture-run',
      targetTaskId: 'fixture-task',
      targetCodeSessionId: 'fixture-code-a',
      getterSetId: GETTER_SET_ID,
      moduleSha256: '0'.repeat(64),
      copiedAsarSha256: '1'.repeat(64),
      setupDeadlineMs: 1000,
      pollIntervalMs: 10,
    };

    const probe = await attachProbe({
      config,
      selectReceiver: adapter.selectReceiver,
      approvedHostProjection: projectApprovedHost,
      processIdentity: {
        pid: process.pid,
        processStartTicks: '1',
        uid: process.getuid(),
      },
      now: () => 2000,
    });

    assert.deepEqual(queryCalls, []);
    assert.equal(probe.state, 'disarmed');

    const binding = probe.bootstrap;
    const arm = {
      schema: ARM_SCHEMA,
      runId: binding.runId,
      configSha256: binding.configSha256,
      moduleSha256: binding.moduleSha256,
      copiedAsarSha256: binding.copiedAsarSha256,
      appStartNonce: binding.appStartNonce,
      pid: binding.pid,
      processStartTicks: binding.processStartTicks,
      targetTaskId: binding.targetTaskId,
      targetCodeSessionId: binding.targetCodeSessionId,
      queryGeneration: binding.queryGeneration,
      getterSetId: binding.getterSetId,
      maxSamples: 1,
      minIntervalMs: 5000,
      observationWindowMs: 30000,
      perGetterTimeoutMs: 1000,
    };

    await writeFile(
      join(runDirectory, 'arm.json'),
      JSON.stringify(arm),
      {
        flag: 'wx',
        mode: 0o600,
      },
    );

    await probe.acceptArm();
    const result = await probe.sample();

    assert.equal(result.result, 'complete');
    assert.deepEqual(queryCalls, [
      'accountInfo',
      'getContextUsage',
      'listPermissionRules',
    ]);
    assert.equal(
      result.observation.fields.hostBefore.value.modeEvent.mode,
      'default',
    );
    assert.equal(
      result.observation.fields.hostAfter.value.modeEvent.mode,
      'default',
    );
    assert.deepEqual(
      result.observation.fields.hostBefore.value
        .selectedExecutorReport,
      result.observation.fields.hostAfter.value
        .selectedExecutorReport,
    );
    assert.deepEqual(
      result.observation.fields.hostAfter.value
        .selectedExecutorReport,
      {
        taskId: 'fixture-task',
        cliPid: 4321,
        cliPidAtMs: 1200,
        cliReportedVersion: 'fixture-version',
        currentCodeSessionId: 'fixture-code-a',
        queryGeneration: 5,
        historicProvenance: 'unknown',
        queryToOsAssociation: 'unknown',
        reportBasis:
          'manager-retained-report; not independent OS association',
      },
    );
    assert.ok(unavailableChecks > 0);

    const previousView = adapter.selectReceiver('fixture-task');

    rawRecord = {
      ...rawRecord,
      inputStream: {},
    };

    const replacementView = adapter.selectReceiver('fixture-task');

    assert.notEqual(replacementView, previousView);
    assert.equal(
      adapter.selectReceiver('fixture-task'),
      replacementView,
    );

    adapter.dispose();
  } finally {
    await rm(root, {
      recursive: true,
      force: true,
    });
  }
});
