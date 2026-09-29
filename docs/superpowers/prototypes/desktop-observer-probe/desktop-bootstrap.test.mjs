import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import {
  mkdir,
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
  BOOTSTRAP_SCHEMA,
  CONFIG_SCHEMA,
  GETTER_SET_ID,
  SAMPLE_SCHEMA,
} from './observer-probe.mjs';
import { bootDesktopObserver } from './desktop-adapter.mjs';

const sha256 = bytes =>
  createHash('sha256').update(bytes).digest('hex');

const delay = milliseconds =>
  new Promise(resolve => setTimeout(resolve, milliseconds));

async function waitForJson(path, timeoutMs) {
  const deadline = Date.now() + timeoutMs;

  while (true) {
    try {
      return JSON.parse(await readFile(path, 'utf8'));
    } catch (error) {
      if (error?.code !== 'ENOENT') throw error;
      if (Date.now() >= deadline) {
        throw new Error('timed out waiting for observer output');
      }
    }

    await delay(10);
  }
}

async function makeFixture(root, name) {
  const fixtureRoot = join(root, name);
  const runDirectory = join(fixtureRoot, 'run');
  const configPath = join(fixtureRoot, 'config.json');
  const modulePath = join(fixtureRoot, 'desktopRuntimeObserver.js');
  const copiedAsarPath = join(fixtureRoot, 'app.asar');

  await mkdir(fixtureRoot, { mode: 0o700 });
  await mkdir(runDirectory, { mode: 0o700 });

  const moduleBytes = Buffer.from(
    'export const syntheticObserverArtifact = true;\n',
  );
  const copiedAsarBytes = Buffer.from(
    'synthetic physical archive bytes\n',
  );

  await writeFile(modulePath, moduleBytes);
  await writeFile(copiedAsarPath, copiedAsarBytes);

  const calls = {
    getters: [],
    selectedTaskIds: [],
  };

  const query = {
    async accountInfo() {
      calls.getters.push('accountInfo');
      return {
        apiProvider: 'firstParty',
        tokenSource: 'fixture',
      };
    },
    async getContextUsage() {
      calls.getters.push('getContextUsage');
      return {
        model: 'fixture-model',
      };
    },
    async listPermissionRules() {
      calls.getters.push('listPermissionRules');
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

  const record = {
    sessionId: `${name}-task`,
    cliSessionId: `${name}-code-session`,
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

  const manager = {
    sessions: {
      get(taskId) {
        calls.selectedTaskIds.push(taskId);
        return taskId === record.sessionId ? record : undefined;
      },
      values() {
        throw new Error('record enumeration is forbidden');
      },
      [Symbol.iterator]() {
        throw new Error('record enumeration is forbidden');
      },
    },
    cliOAuthTokenKeeper: {
      spawnAccountOf(selectedRecord) {
        assert.equal(selectedRecord, record);
        return {
          accountUuid: 'fixture-account',
          orgId: 'fixture-org',
        };
      },
    },
  };

  const config = {
    schema: CONFIG_SCHEMA,
    runDirectory,
    runId: `${name}-run`,
    targetTaskId: record.sessionId,
    targetCodeSessionId: record.cliSessionId,
    getterSetId: GETTER_SET_ID,
    moduleSha256: sha256(moduleBytes),
    copiedAsarSha256: sha256(copiedAsarBytes),
    setupDeadlineMs: 1000,
    pollIntervalMs: 10,
  };

  await writeFile(configPath, JSON.stringify(config), {
    flag: 'wx',
    mode: 0o600,
  });

  return {
    calls,
    config,
    configPath,
    copiedAsarPath,
    manager,
    modulePath,
    runDirectory,
    boot() {
      return bootDesktopObserver({
        manager,
        isUnavailable: selectedRecord => selectedRecord !== record,
        effectiveCuAllowedApps: selectedRecord =>
          selectedRecord.effectiveCuAllowedApps,
        effectiveCuGrantFlags: selectedRecord =>
          selectedRecord.effectiveCuGrantFlags,
        modulePath,
        copiedAsarPath,
      });
    },
  };
}

test(
  'public Desktop boot verifies artifacts, waits for an exact arm, and samples only the selected task',
  { timeout: 12_000 },
  async () => {
    const root = await mkdtemp(join(tmpdir(), 'desktop-bootstrap-'));
    const previousConfigPath =
      process.env.PROVINGKIT_OBSERVER_CONFIG;

    try {
      const fixture = await makeFixture(root, 'accepted');

      process.env.PROVINGKIT_OBSERVER_CONFIG = fixture.configPath;

      const completion = fixture.boot();

      assert.ok(completion instanceof Promise);

      const bootstrap = await waitForJson(
        join(fixture.runDirectory, 'bootstrap.json'),
        1000,
      );

      assert.equal(bootstrap.schema, BOOTSTRAP_SCHEMA);
      assert.equal(bootstrap.runId, fixture.config.runId);
      assert.equal(
        bootstrap.targetTaskId,
        fixture.config.targetTaskId,
      );
      assert.equal(
        bootstrap.targetCodeSessionId,
        fixture.config.targetCodeSessionId,
      );
      assert.equal(
        bootstrap.moduleSha256,
        fixture.config.moduleSha256,
      );
      assert.equal(
        bootstrap.copiedAsarSha256,
        fixture.config.copiedAsarSha256,
      );
      assert.deepEqual(fixture.calls.getters, []);
      assert.ok(fixture.calls.selectedTaskIds.length > 0);
      assert.ok(
        fixture.calls.selectedTaskIds.every(
          taskId => taskId === fixture.config.targetTaskId,
        ),
      );

      const arm = {
        schema: ARM_SCHEMA,
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
        maxSamples: 1,
        minIntervalMs: 5000,
        observationWindowMs: 15_000,
        perGetterTimeoutMs: 1000,
      };

      await writeFile(
        join(fixture.runDirectory, 'arm.json'),
        JSON.stringify(arm),
        {
          flag: 'wx',
          mode: 0o600,
        },
      );

      assert.equal(await completion, true);

      const sample = JSON.parse(
        await readFile(
          join(fixture.runDirectory, 'sample-000001.json'),
          'utf8',
        ),
      );

      assert.equal(sample.schema, SAMPLE_SCHEMA);
      assert.equal(sample.result, 'complete');
      assert.equal(
        sample.binding.targetTaskId,
        fixture.config.targetTaskId,
      );
      assert.deepEqual(fixture.calls.getters, [
        'accountInfo',
        'getContextUsage',
        'listPermissionRules',
      ]);
      assert.ok(
        fixture.calls.selectedTaskIds.every(
          taskId => taskId === fixture.config.targetTaskId,
        ),
      );

      const rejected = await makeFixture(root, 'rejected');

      await writeFile(
        rejected.modulePath,
        'corrupted observer artifact\n',
      );

      process.env.PROVINGKIT_OBSERVER_CONFIG = rejected.configPath;

      const rejectedCompletion = rejected.boot();

      assert.ok(rejectedCompletion instanceof Promise);
      assert.equal(await rejectedCompletion, false);
      assert.deepEqual(rejected.calls.getters, []);
      assert.deepEqual(rejected.calls.selectedTaskIds, []);
      await assert.rejects(
        readFile(join(rejected.runDirectory, 'bootstrap.json')),
        error => error?.code === 'ENOENT',
      );
    } finally {
      if (previousConfigPath === undefined) {
        delete process.env.PROVINGKIT_OBSERVER_CONFIG;
      } else {
        process.env.PROVINGKIT_OBSERVER_CONFIG =
          previousConfigPath;
      }

      await rm(root, {
        recursive: true,
        force: true,
      });
    }
  },
);
