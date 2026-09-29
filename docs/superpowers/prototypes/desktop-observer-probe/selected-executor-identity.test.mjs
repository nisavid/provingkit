import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import {
  chmod,
  mkdir,
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
import { inspectProbeSample } from './probe-reader.mjs';
import {
  observeSelectedLinuxExecutor,
} from './selected-executor-linux-identity.mjs';

test('selected executor report reaches a bounded synthetic Linux observation without proving association', async () => {
  const root = await mkdtemp(join(tmpdir(), 'selected-executor-'));
  const runDirectory = join(root, 'run');
  const selectedRoot = join(root, 'synthetic-proc');
  const pid = 4321;
  const processDirectory = join(selectedRoot, String(pid));
  const executableBytes = Buffer.from('synthetic executable bytes\n');

  await chmod(root, 0o700);
  await mkdir(runDirectory, { mode: 0o700 });
  await mkdir(processDirectory, { recursive: true, mode: 0o700 });

  const statFields = [
    'S',
    ...Array(18).fill('0'),
    '424242',
  ];

  await writeFile(
    join(processDirectory, 'stat'),
    `${pid} (fixture worker) ${statFields.join(' ')}\n`,
  );
  await writeFile(
    join(processDirectory, 'exe'),
    executableBytes,
    { mode: 0o700 },
  );

  try {
    const query = {
      async accountInfo() {
        return {
          apiProvider: 'firstParty',
          tokenSource: 'fixture',
        };
      },
      async getContextUsage() {
        return { model: 'fixture-model' };
      },
      async listPermissionRules() {
        return {
          state: {
            rules: [],
            workspaceDirectories: [],
            originalCwd: '/fixture',
            managedOnly: false,
          },
        };
      },
    };

    const record = {
      taskId: 'fixture-task',
      codeSessionId: 'fixture-code',
      generation: 7,
      query,
      inputStream: {},
      host: {
        selectedExecutorReport: {
          taskId: 'fixture-task',
          cliPid: pid,
          cliPidAtMs: 1700000000000,
          cliReportedVersion: 'fixture-version',
          currentCodeSessionId: 'fixture-code',
        },
      },
    };

    const selectReceiver = taskId =>
      taskId === record.taskId ? record : null;

    let clock = 2000;
    const probe = await attachProbe({
      config: {
        schema: 'desktop-observer.probe-config.v1',
        runDirectory,
        runId: 'fixture-run',
        targetTaskId: record.taskId,
        targetCodeSessionId: record.codeSessionId,
        getterSetId: GETTER_SET_ID,
        moduleSha256: '0'.repeat(64),
        copiedAsarSha256: '1'.repeat(64),
        setupDeadlineMs: 1000,
        pollIntervalMs: 10,
      },
      selectReceiver,
      approvedHostProjection: projectApprovedHost,
      processIdentity: {
        pid: process.pid,
        processStartTicks: '1',
        uid: process.getuid(),
      },
      now: () => clock++,
    });

    const binding = probe.bootstrap;
    await writeFile(
      join(runDirectory, 'arm.json'),
      JSON.stringify({
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
      }),
      { flag: 'wx', mode: 0o600 },
    );

    await probe.acceptArm();
    const sample = await probe.sample();
    const inspection = inspectProbeSample(
      JSON.stringify(sample),
      sample.binding,
      {
        now: sample.observation.collection.endedAt + 1,
        maximumAgeMs: 1000,
      },
    );

    assert.equal(inspection.state, 'usable-partial');

    const beforeReport =
      inspection.sample.observation.fields.hostBefore.value
        .selectedExecutorReport;
    const afterReport =
      inspection.sample.observation.fields.hostAfter.value
        .selectedExecutorReport;

    assert.deepEqual(beforeReport, afterReport);
    assert.deepEqual(afterReport, {
      taskId: 'fixture-task',
      cliPid: pid,
      cliPidAtMs: 1700000000000,
      cliReportedVersion: 'fixture-version',
      currentCodeSessionId: 'fixture-code',
      queryGeneration: 7,
      historicProvenance: 'unknown',
      queryToOsAssociation: 'unknown',
      reportBasis:
        'manager-retained-report; not independent OS association',
    });

    assert.equal(
      inspection.sample.observation.fields.hostBefore.source,
      'Desktop manager projection',
    );
    assert.equal(
      inspection.sample.observation.fields.hostAfter.source,
      'Desktop manager projection',
    );

    const linuxObservation =
      await observeSelectedLinuxExecutor(
        afterReport,
        selectedRoot,
      );

    assert.deepEqual(linuxObservation, {
      state: 'observed-partial',
      qualification: 'unqualified',
      selectedReport: afterReport,
      linuxIdentity: {
        pid,
        processStartTicks: '424242',
        ownerUid: process.getuid(),
        executable: {
          dev: linuxObservation.linuxIdentity.executable.dev,
          ino: linuxObservation.linuxIdentity.executable.ino,
          size: String(executableBytes.length),
          sha256: createHash('sha256')
            .update(executableBytes)
            .digest('hex'),
        },
      },
      queryToOsAssociation: 'unknown',
    });

    const unavailable = await observeSelectedLinuxExecutor(
      {
        ...afterReport,
        cliPid: null,
      },
      join(root, 'must-not-be-read'),
    );

    assert.deepEqual(unavailable, {
      state: 'unknown',
      reason: 'selected-pid-unavailable',
      qualification: 'unqualified',
      queryToOsAssociation: 'unknown',
    });

    const tampered = structuredClone(sample);
    tampered.observation.fields.hostBefore.value
      .selectedExecutorReport.queryToOsAssociation = 'proven';
    tampered.observation.fields.hostAfter.value
      .selectedExecutorReport.queryToOsAssociation = 'proven';

    assert.deepEqual(
      inspectProbeSample(
        JSON.stringify(tampered),
        sample.binding,
        {
          now: sample.observation.collection.endedAt + 1,
          maximumAgeMs: 1000,
        },
      ),
      {
        state: 'unknown',
        reason: 'invalid-sample',
        qualification: 'unqualified',
      },
    );
  } finally {
    await rm(root, {
      recursive: true,
      force: true,
    });
  }
});
