import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import {
  chmod,
  lstat,
  mkdir,
  mkdtemp,
  open,
  rename,
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

function syntheticStat(pid, processStartTicks) {
  const fields = [
    'S',
    ...Array(18).fill('0'),
    processStartTicks,
  ];

  return `${pid} (fixture worker) ${fields.join(' ')}\n`;
}

async function writeSyntheticProcess(
  processDirectory,
  {
    pid = 4321,
    processStartTicks = '424242',
    executableBytes = Buffer.from(
      'synthetic executable bytes\n',
    ),
  } = {},
) {
  await mkdir(processDirectory, {
    recursive: true,
    mode: 0o700,
  });
  await writeFile(
    join(processDirectory, 'stat'),
    syntheticStat(pid, processStartTicks),
  );
  await writeFile(
    join(processDirectory, 'exe'),
    executableBytes,
    { mode: 0o700 },
  );
}

test('malformed observation inputs are rejected before boot-ID, sample, or process I/O', async t => {
  const missingMaximumAge = acquisitionInput();
  delete missingMaximumAge.maximumAgeMs;

  const incompleteBinding = bindingFor();
  delete incompleteBinding.linuxBootId;

  const cases = [
    {
      name: 'unknown input key',
      input: {
        ...acquisitionInput(),
        selectedRoot: '/caller-selected-root',
      },
    },
    {
      name: 'missing input key',
      input: missingMaximumAge,
    },
    {
      name: 'sequence below range',
      input: {
        ...acquisitionInput(),
        sequence: 0,
      },
    },
    {
      name: 'sequence above range',
      input: {
        ...acquisitionInput(),
        sequence: 4,
        afterSequence: 3,
      },
    },
    {
      name: 'afterSequence is not the predecessor',
      input: {
        ...acquisitionInput(),
        afterSequence: 1,
      },
    },
    {
      name: 'maximumAgeMs below range',
      input: {
        ...acquisitionInput(),
        maximumAgeMs: 0,
      },
    },
    {
      name: 'maximumAgeMs above range',
      input: {
        ...acquisitionInput(),
        maximumAgeMs: 30001,
      },
    },
    {
      name: 'different expected UID',
      input: {
        ...acquisitionInput(),
        expectedUid: process.getuid() + 1,
      },
    },
    {
      name: 'relative run directory',
      input: {
        ...acquisitionInput(),
        runDirectory: 'fixture/run',
      },
    },
    {
      name: 'oversized run directory',
      input: {
        ...acquisitionInput(),
        runDirectory: `/${'a'.repeat(1024)}`,
      },
    },
    {
      name: 'run directory with control characters',
      input: {
        ...acquisitionInput(),
        runDirectory: '/fixture/\nrun',
      },
    },
    {
      name: 'incomplete binding',
      input: {
        ...acquisitionInput(),
        expectedBinding: incompleteBinding,
      },
    },
    {
      name: 'binding with an unknown key',
      input: {
        ...acquisitionInput(),
        expectedBinding: {
          ...bindingFor(),
          selectedRoot: '/caller-selected-root',
        },
      },
    },
    {
      name: 'binding with a malformed digest',
      input: {
        ...acquisitionInput(),
        expectedBinding: {
          ...bindingFor(),
          configSha256: 'not-a-digest',
        },
      },
    },
  ];

  for (const fixture of cases) {
    await t.test(fixture.name, async () => {
      let bootIdReads = 0;
      let sampleReads = 0;
      let processReads = 0;

      const observer = createSelectedLinuxExecutorObserver({
        processRoot: '/synthetic-proc',
        readProbeSample: async () => {
          sampleReads += 1;
          return usableInspection();
        },
        getuid: () => process.getuid(),
        now: () => 1020,
        monotonicNow: () => 5020,
        readLinuxBootId: async () => {
          bootIdReads += 1;
          return LINUX_BOOT_ID;
        },
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
        await observer(fixture.input),
        unknownSample,
      );
      assert.equal(bootIdReads, 0);
      assert.equal(sampleReads, 0);
      assert.equal(processReads, 0);
    });
  }
});

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

test('acquisition clock rollback rejects process I/O even when the regressed reading remains fresh', async t => {
  const cases = [
    {
      name: 'wall clock only',
      wallTimes: [1020, 1015],
      monotonicTimes: [5020, 5020],
    },
    {
      name: 'monotonic clock only',
      wallTimes: [1020, 1020],
      monotonicTimes: [5020, 5015],
    },
  ];

  for (const fixture of cases) {
    await t.test(fixture.name, async () => {
      const wallTimes = [...fixture.wallTimes];
      const monotonicTimes = [
        ...fixture.monotonicTimes,
      ];
      let sampleReads = 0;
      let processDirectoryReads = 0;
      let processOpens = 0;

      const observer = createSelectedLinuxExecutorObserver({
        processRoot: '/synthetic-proc',
        readProbeSample: async input => {
          sampleReads += 1;
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
        lstat: async () => {
          processDirectoryReads += 1;
          return {
            dev: 1n,
            ino: 2n,
            mode: 0o40700n,
            uid: BigInt(process.getuid()),
            gid: 3n,
            isDirectory: () => true,
            isSymbolicLink: () => false,
          };
        },
        open: async () => {
          processOpens += 1;
          throw new Error('process path must not be opened');
        },
      });

      assert.deepEqual(
        await observer(acquisitionInput()),
        unknownSample,
      );
      assert.equal(sampleReads, 1);
      assert.equal(processDirectoryReads, 0);
      assert.equal(processOpens, 0);
      assert.deepEqual(wallTimes, []);
      assert.deepEqual(monotonicTimes, []);
    });
  }
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

test('freshness is rechecked after a delayed later stat read before the executable is opened', async () => {
  const root = await mkdtemp(
    join(tmpdir(), 'selected-executor-delay-'),
  );
  const processRoot = join(root, 'synthetic-proc');
  const processDirectory = join(processRoot, '4321');

  await writeSyntheticProcess(processDirectory);

  try {
    let wallChecks = 0;
    let monotonicChecks = 0;
    const openedPaths = [];

    const observer = createSelectedLinuxExecutorObserver({
      processRoot,
      readProbeSample: async () => usableInspection(),
      getuid: () => process.getuid(),
      now: () => {
        wallChecks += 1;
        return wallChecks < 6 ? 1020 : 2001;
      },
      monotonicNow: () => {
        monotonicChecks += 1;
        return monotonicChecks < 6 ? 5020 : 6001;
      },
      readLinuxBootId: async () => LINUX_BOOT_ID,
      lstat,
      open: async (...args) => {
        openedPaths.push(args[0]);
        return open(...args);
      },
    });

    assert.deepEqual(
      await observer(acquisitionInput()),
      unknownSample,
    );
    assert.equal(wallChecks, 6);
    assert.equal(monotonicChecks, 6);
    assert.equal(openedPaths[0], processDirectory);
    assert.equal(
      openedPaths.filter(path => path.endsWith('/stat'))
        .length,
      2,
    );
    assert.equal(
      openedPaths.filter(path => path.endsWith('/exe')).length,
      0,
    );
    assert.ok(
      openedPaths
        .slice(1)
        .every(path =>
          path.startsWith('/proc/self/fd/'),
        ),
    );
  } finally {
    await rm(root, {
      recursive: true,
      force: true,
    });
  }
});

test('replacement of the numeric PID path cannot redirect later child opens', async () => {
  const root = await mkdtemp(
    join(tmpdir(), 'selected-executor-replacement-'),
  );
  const processRoot = join(root, 'synthetic-proc');
  const processDirectory = join(processRoot, '4321');
  const retainedDirectory = join(processRoot, 'retained-4321');
  const selectedExecutable = Buffer.from(
    'selected executable bytes\n',
  );
  const replacementExecutable = Buffer.from(
    'replacement executable bytes\n',
  );

  await writeSyntheticProcess(processDirectory, {
    processStartTicks: '424242',
    executableBytes: selectedExecutable,
  });

  try {
    let replacementInstalled = false;
    let directoryDescriptor;
    const openedPaths = [];
    const inspectedPaths = [];

    const observer = createSelectedLinuxExecutorObserver({
      processRoot,
      readProbeSample: async () => usableInspection(),
      getuid: () => process.getuid(),
      now: () => 1020,
      monotonicNow: () => 5020,
      readLinuxBootId: async () => LINUX_BOOT_ID,
      lstat: async (...args) => {
        inspectedPaths.push(args[0]);
        return lstat(...args);
      },
      open: async (...args) => {
        const handle = await open(...args);
        openedPaths.push(args[0]);

        if (args[0] === processDirectory) {
          directoryDescriptor = handle.fd;
        } else if (
          !replacementInstalled &&
          args[0] ===
            `/proc/self/fd/${directoryDescriptor}/stat`
        ) {
          replacementInstalled = true;
          await rename(
            processDirectory,
            retainedDirectory,
          );
          await writeSyntheticProcess(processDirectory, {
            processStartTicks: '999999',
            executableBytes: replacementExecutable,
          });
        }

        return handle;
      },
    });

    const observed = await observer(acquisitionInput());
    const descriptorRoot =
      `/proc/self/fd/${directoryDescriptor}`;

    assert.equal(replacementInstalled, true);
    assert.deepEqual(inspectedPaths, [
      processDirectory,
      processDirectory,
    ]);
    assert.deepEqual(openedPaths, [
      processDirectory,
      `${descriptorRoot}/stat`,
      `${descriptorRoot}/stat`,
      `${descriptorRoot}/exe`,
      `${descriptorRoot}/stat`,
      `${descriptorRoot}/exe`,
    ]);
    assert.equal(observed.state, 'observed-partial');
    assert.equal(
      observed.linuxIdentity.processStartTicks,
      '424242',
    );
    assert.equal(
      observed.linuxIdentity.executable.sha256,
      createHash('sha256')
        .update(selectedExecutable)
        .digest('hex'),
    );
    assert.notEqual(
      observed.linuxIdentity.executable.sha256,
      createHash('sha256')
        .update(replacementExecutable)
        .digest('hex'),
    );
  } finally {
    await rm(root, {
      recursive: true,
      force: true,
    });
  }
});

test('an unknown process root is rejected without I/O and a valid fixture uses only the hardwired process root', async () => {
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

  await writeFile(
    join(processDirectory, 'stat'),
    syntheticStat(pid, '424242'),
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
    let processDirectoryDescriptor;
    let bootIdReads = 0;
    let sampleReads = 0;

    const observer = createSelectedLinuxExecutorObserver({
      processRoot,
      readProbeSample: async input => {
        sampleReads += 1;
        return readProbeSample(input);
      },
      getuid: () => process.getuid(),
      now: () => acquisitionNow++,
      monotonicNow: () => acquisitionMonotonicNow++,
      readLinuxBootId: async () => {
        bootIdReads += 1;
        return LINUX_BOOT_ID;
      },
      lstat: async (...args) => {
        processPaths.push(args[0]);
        return lstat(...args);
      },
      open: async (...args) => {
        processPaths.push(args[0]);
        processOpenPaths.push(args[0]);
        const handle = await open(...args);

        if (args[0] === processDirectory) {
          processDirectoryDescriptor = handle.fd;
        }

        return handle;
      },
    });

    const validInput = {
      runDirectory,
      sequence: sample.sequence,
      expectedBinding: sample.binding,
      maximumAgeMs: 1000,
      afterSequence: 0,
      expectedUid: process.getuid(),
    };

    assert.deepEqual(
      await observer({
        ...validInput,
        selectedRoot: forbiddenCallerRoot,
      }),
      unknownSample,
    );
    assert.equal(bootIdReads, 0);
    assert.equal(sampleReads, 0);
    assert.deepEqual(processPaths, []);
    assert.deepEqual(processOpenPaths, []);

    const observed = await observer(validInput);

    assert.equal(bootIdReads, 2);
    assert.equal(sampleReads, 2);

    const selectedReport =
      sample.observation.fields.hostAfter.value
        .selectedExecutorReport;

    assert.deepEqual(
      sample.observation.fields.hostBefore.value
        .selectedExecutorReport,
      selectedReport,
    );
    const descriptorRoot =
      `/proc/self/fd/${processDirectoryDescriptor}`;

    assert.deepEqual(processOpenPaths, [
      processDirectory,
      `${descriptorRoot}/stat`,
      `${descriptorRoot}/stat`,
      `${descriptorRoot}/exe`,
      `${descriptorRoot}/stat`,
      `${descriptorRoot}/exe`,
    ]);
    assert.ok(
      processPaths.every(
        path =>
          path === processDirectory ||
          path.startsWith(`${descriptorRoot}/`),
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
