import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import {
  chmod,
  lstat,
  mkdir,
  mkdtemp,
  open,
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
  MONOTONIC_CLOCK_ID,
  SELECTED_EXECUTOR_REPORT_BASIS,
} from './observer-contract.mjs';
import { readProbeSample } from './read-probe-file.mjs';
import {
  createSelectedLinuxExecutorObserver,
} from './selected-executor-linux-identity-internal.mjs';

const LINUX_BOOT_ID = '11111111-2222-4333-8444-555555555555';

const unknownSample = {
  state: 'unknown',
  reason: 'selected-sample-unavailable-or-changed',
  qualification: 'unqualified',
  queryToOsAssociation: 'unknown',
};

const reportFor = ({
  taskId = 'fixture-task',
  cliPid = 4321,
  codeSessionId = 'fixture-code',
  generation = 7,
} = {}) => ({
  taskId,
  cliPid,
  cliPidAtMs: 1700000000000,
  cliReportedVersion: 'fixture-version',
  currentCodeSessionId: codeSessionId,
  queryGeneration: generation,
  historicProvenance: 'unknown',
  queryToOsAssociation: 'unknown',
  reportBasis: SELECTED_EXECUTOR_REPORT_BASIS,
});

const bindingFor = ({
  taskId = 'fixture-task',
  codeSessionId = 'fixture-code',
  generation = 7,
} = {}) => ({
  runId: 'fixture-run',
  configSha256: '0'.repeat(64),
  moduleSha256: '1'.repeat(64),
  copiedAsarSha256: '2'.repeat(64),
  appStartNonce: '3'.repeat(64),
  pid: 99,
  processStartTicks: '10',
  targetTaskId: taskId,
  targetCodeSessionId: codeSessionId,
  queryGeneration: generation,
  getterSetId: GETTER_SET_ID,
  monotonicClockId: MONOTONIC_CLOCK_ID,
  linuxBootId: LINUX_BOOT_ID,
});

function usableInspection({
  binding = bindingFor(),
  beforeReport = reportFor(),
  afterReport = beforeReport,
  sequence = 1,
  observedAt = 1000,
  endedAt = 1010,
  observedAtMonotonicMs = 5000,
  endedAtMonotonicMs = 5010,
} = {}) {
  return {
    state: 'usable-partial',
    qualification: 'unqualified',
    sample: {
      binding,
      sequence,
      observedAt,
      observedAtMonotonicMs,
      observation: {
        collection: {
          startedAt: observedAt,
          endedAt,
          startedAtMonotonicMs: observedAtMonotonicMs,
          endedAtMonotonicMs,
          hostChangedDuringRead: false,
        },
        fields: {
          hostBefore: {
            value: {
              selectedExecutorReport: beforeReport,
            },
          },
          hostAfter: {
            value: {
              selectedExecutorReport: afterReport,
            },
          },
        },
      },
    },
  };
}

function acquisitionInput({
  expectedBinding = bindingFor(),
  expectedUid = process.getuid(),
} = {}) {
  return {
    runDirectory: '/fixture/run',
    sequence: 1,
    expectedBinding,
    maximumAgeMs: 1000,
    afterSequence: 0,
    expectedUid,
  };
}

test('foreign process owner is rejected before any process file is opened', async () => {
  const inspection = usableInspection();
  let processFileOpens = 0;

  const observer = createSelectedLinuxExecutorObserver({
    processRoot: '/synthetic-proc',
    readProbeSample: async () => inspection,
    getuid: () => process.getuid(),
    now: () => 1020,
    monotonicNow: () => 5020,
    readLinuxBootId: async () => LINUX_BOOT_ID,
    lstat: async path => {
      assert.equal(path, '/synthetic-proc/4321');

      return {
        dev: 1n,
        ino: 2n,
        mode: 0o40700n,
        uid: BigInt(process.getuid() + 1),
        gid: 3n,
        isDirectory: () => true,
        isSymbolicLink: () => false,
      };
    },
    open: async () => {
      processFileOpens += 1;
      throw new Error('process file must not be opened');
    },
  });

  assert.deepEqual(
    await observer(acquisitionInput()),
    {
      state: 'unknown',
      reason: 'linux-identity-unavailable-or-changed',
      qualification: 'unqualified',
      queryToOsAssociation: 'unknown',
    },
  );
  assert.equal(processFileOpens, 0);
});

test('sample binding, report mismatch, and stale acquisition failures perform zero process reads', async t => {
  const mismatchedReports = usableInspection({
    afterReport: reportFor({ cliPid: 4322 }),
  });

  const cases = [
    {
      name: 'binding mismatch',
      acquisition: {
        state: 'unknown',
        reason: 'binding-mismatch',
        qualification: 'unqualified',
      },
    },
    {
      name: 'report mismatch',
      acquisition: mismatchedReports,
    },
    {
      name: 'stale sample',
      acquisition: {
        state: 'unknown',
        reason: 'expired',
        qualification: 'unqualified',
      },
    },
  ];

  for (const fixture of cases) {
    await t.test(fixture.name, async () => {
      let processReads = 0;

      const observer = createSelectedLinuxExecutorObserver({
        processRoot: '/synthetic-proc',
        readProbeSample: async () => fixture.acquisition,
        getuid: () => process.getuid(),
        now: () => 1020,
        monotonicNow: () => 5020,
        readLinuxBootId: async () => LINUX_BOOT_ID,
        lstat: async () => {
          processReads += 1;
          throw new Error('process directory must not be read');
        },
        open: async () => {
          processReads += 1;
          throw new Error('process file must not be opened');
        },
      });

      assert.deepEqual(
        await observer(acquisitionInput()),
        unknownSample,
      );
      assert.equal(processReads, 0);
    });
  }
});

test('partial wall rollback cannot permit selected process reads after monotonic expiry', async () => {
  let processReads = 0;
  let acquisitions = 0;

  const observer = createSelectedLinuxExecutorObserver({
    processRoot: '/synthetic-proc',
    readProbeSample: async input => {
      acquisitions += 1;
      assert.equal(input.now, 1050);
      assert.equal(input.monotonicNow, 5200);
      assert.equal(input.monotonicClockId, MONOTONIC_CLOCK_ID);
      assert.equal(input.linuxBootId, LINUX_BOOT_ID);
      return {
        state: 'unknown',
        reason: 'expired',
        qualification: 'unqualified',
      };
    },
    getuid: () => process.getuid(),
    now: () => 1050,
    monotonicNow: () => 5200,
    readLinuxBootId: async () => LINUX_BOOT_ID,
    lstat: async () => {
      processReads += 1;
      throw new Error('process directory must not be read');
    },
    open: async () => {
      processReads += 1;
      throw new Error('process file must not be opened');
    },
  });

  assert.deepEqual(
    await observer(acquisitionInput()),
    unknownSample,
  );
  assert.equal(acquisitions, 1);
  assert.equal(processReads, 0);
});

test('delayed acquisition and owner check reject expiry before process-file opens', async t => {
  const cases = [
    {
      name: 'acquisition delay',
      wallTimes: [1020, 2001],
      monotonicTimes: [5020, 6001],
      expectedDirectoryReads: 0,
    },
    {
      name: 'owner-check delay',
      wallTimes: [1020, 1020, 2001],
      monotonicTimes: [5020, 5020, 6001],
      expectedDirectoryReads: 1,
    },
  ];

  for (const fixture of cases) {
    await t.test(fixture.name, async () => {
      const wallTimes = [...fixture.wallTimes];
      const monotonicTimes = [...fixture.monotonicTimes];
      let processDirectoryReads = 0;
      let processFileOpens = 0;

      const observer = createSelectedLinuxExecutorObserver({
        processRoot: '/synthetic-proc',
        readProbeSample: async input => {
          assert.equal(input.now, 1020);
          assert.equal(input.monotonicNow, 5020);
          assert.equal(
            input.monotonicClockId,
            MONOTONIC_CLOCK_ID,
          );
          assert.equal(input.linuxBootId, LINUX_BOOT_ID);
          return usableInspection();
        },
        getuid: () => process.getuid(),
        now: () => wallTimes.shift(),
        monotonicNow: () => monotonicTimes.shift(),
        readLinuxBootId: async () => LINUX_BOOT_ID,
        lstat: async path => {
          processDirectoryReads += 1;
          assert.equal(path, '/synthetic-proc/4321');
          return {
            uid: BigInt(process.getuid()),
            isDirectory: () => true,
            isSymbolicLink: () => false,
          };
        },
        open: async () => {
          processFileOpens += 1;
          throw new Error('process file must not be opened');
        },
      });

      assert.deepEqual(
        await observer(acquisitionInput()),
        unknownSample,
      );
      assert.equal(
        processDirectoryReads,
        fixture.expectedDirectoryReads,
      );
      assert.equal(processFileOpens, 0);
      assert.deepEqual(wallTimes, []);
      assert.deepEqual(monotonicTimes, []);
    });
  }
});

test('a validated fixture sample observes only its selected synthetic process and retains unqualified evidence', async () => {
  const root = await mkdtemp(join(tmpdir(), 'selected-executor-'));
  const runDirectory = join(root, 'run');
  const processRoot = join(root, 'synthetic-proc');
  const forbiddenCallerRoot = join(root, 'caller-selected-root');
  const pid = 4321;
  const processDirectory = join(processRoot, String(pid));
  const executableBytes = Buffer.from(
    'synthetic executable bytes\n',
  );

  await chmod(root, 0o700);
  await mkdir(runDirectory, { mode: 0o700 });
  await mkdir(processDirectory, {
    recursive: true,
    mode: 0o700,
  });

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
        monotonicClockId: MONOTONIC_CLOCK_ID,
        linuxBootId: LINUX_BOOT_ID,
      },
      now: () => clock++,
      monotonicNow: () => clock++,
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
        monotonicClockId: binding.monotonicClockId,
        linuxBootId: binding.linuxBootId,
        maxSamples: 1,
        minIntervalMs: 5000,
        observationWindowMs: 30000,
        perGetterTimeoutMs: 1000,
      }),
      { flag: 'wx', mode: 0o600 },
    );

    await probe.acceptArm();
    const sample = await probe.sample();
    let acquisitionNow =
      sample.observation.collection.endedAt + 1;
    let acquisitionMonotonicNow =
      sample.observation.collection.endedAtMonotonicMs + 1;
    const processPaths = [];
    const processOpenPaths = [];

    const observer = createSelectedLinuxExecutorObserver({
      processRoot,
      readProbeSample,
      getuid: () => process.getuid(),
      now: () => acquisitionNow++,
      monotonicNow: () => acquisitionMonotonicNow++,
      readLinuxBootId: async () => LINUX_BOOT_ID,
      lstat: async (...args) => {
        processPaths.push(args[0]);
        return lstat(...args);
      },
      open: async (...args) => {
        processPaths.push(args[0]);
        processOpenPaths.push(args[0]);
        return open(...args);
      },
    });

    const observed = await observer({
      runDirectory,
      sequence: sample.sequence,
      expectedBinding: sample.binding,
      maximumAgeMs: 1000,
      afterSequence: 0,
      expectedUid: process.getuid(),
      selectedRoot: forbiddenCallerRoot,
    });

    const selectedReport =
      sample.observation.fields.hostAfter.value
        .selectedExecutorReport;

    assert.deepEqual(
      sample.observation.fields.hostBefore.value
        .selectedExecutorReport,
      selectedReport,
    );
    assert.equal(processOpenPaths.length, 5);
    assert.ok(
      processPaths.every(
        path =>
          path === processDirectory ||
          path.startsWith(`${processDirectory}/`),
      ),
    );
    assert.ok(
      processPaths.every(
        path => !path.startsWith(forbiddenCallerRoot),
      ),
    );

    assert.deepEqual(observed, {
      state: 'observed-partial',
      qualification: 'unqualified',
      sampleEvidence: {
        binding: sample.binding,
        sequence: sample.sequence,
        observedAt: sample.observedAt,
        observedAtMonotonicMs: sample.observedAtMonotonicMs,
        collection: {
          startedAt: sample.observation.collection.startedAt,
          endedAt: sample.observation.collection.endedAt,
          startedAtMonotonicMs:
            sample.observation.collection.startedAtMonotonicMs,
          endedAtMonotonicMs:
            sample.observation.collection.endedAtMonotonicMs,
        },
      },
      selectedReport,
      linuxIdentity: {
        pid,
        processStartTicks: '424242',
        ownerUid: process.getuid(),
        executable: {
          dev: observed.linuxIdentity.executable.dev,
          ino: observed.linuxIdentity.executable.ino,
          size: String(executableBytes.length),
          sha256: createHash('sha256')
            .update(executableBytes)
            .digest('hex'),
        },
      },
      queryToOsAssociation: 'unknown',
    });
  } finally {
    await rm(root, {
      recursive: true,
      force: true,
    });
  }
});
