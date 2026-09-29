import { createHash } from 'node:crypto';
import { constants as fsConstants } from 'node:fs';
import {
  isAbsolute,
  join,
} from 'node:path';
import { TextDecoder } from 'node:util';

const MAX_STAT_BYTES = 4096;
const MAX_EXECUTABLE_BYTES = 256 * 1024 * 1024;
const HASH_BUFFER_BYTES = 64 * 1024;
const MAX_TEXT_BYTES = 256;

const REPORT_KEYS = Object.freeze([
  'taskId',
  'cliPid',
  'cliPidAtMs',
  'cliReportedVersion',
  'currentCodeSessionId',
  'queryGeneration',
  'historicProvenance',
  'queryToOsAssociation',
  'reportBasis',
]);

const unknownSample = () => ({
  state: 'unknown',
  reason: 'selected-sample-unavailable-or-changed',
  qualification: 'unqualified',
  queryToOsAssociation: 'unknown',
});

const unknownLinuxIdentity = () => ({
  state: 'unknown',
  reason: 'linux-identity-unavailable-or-changed',
  qualification: 'unqualified',
  queryToOsAssociation: 'unknown',
});

const isPlainObject = value => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return false;
  }

  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
};

function hasExactKeys(value, keys) {
  if (!isPlainObject(value)) return false;

  const actual = Object.keys(value).sort();
  const expected = [...keys].sort();

  return (
    actual.length === expected.length &&
    actual.every((key, index) => key === expected[index])
  );
}

const hasControlCharacters = value =>
  /[\u0000-\u001f\u007f]/u.test(value);

function isNullableText(value) {
  return (
    value === null ||
    (
      typeof value === 'string' &&
      value.length > 0 &&
      !hasControlCharacters(value) &&
      Buffer.byteLength(value, 'utf8') <= MAX_TEXT_BYTES
    )
  );
}

function normalizeReport(value) {
  if (
    !hasExactKeys(value, REPORT_KEYS) ||
    !isNullableText(value.taskId) ||
    (
      value.cliPid !== null &&
      (
        !Number.isSafeInteger(value.cliPid) ||
        value.cliPid < 1
      )
    ) ||
    (
      value.cliPidAtMs !== null &&
      (
        !Number.isSafeInteger(value.cliPidAtMs) ||
        value.cliPidAtMs < 0
      )
    ) ||
    !isNullableText(value.cliReportedVersion) ||
    !isNullableText(value.currentCodeSessionId) ||
    !Number.isSafeInteger(value.queryGeneration) ||
    value.queryGeneration < 1 ||
    value.historicProvenance !== 'unknown' ||
    value.queryToOsAssociation !== 'unknown' ||
    value.reportBasis !==
      'manager-retained-report; not independent OS association'
  ) {
    return null;
  }

  return {
    taskId: value.taskId,
    cliPid: value.cliPid,
    cliPidAtMs: value.cliPidAtMs,
    cliReportedVersion: value.cliReportedVersion,
    currentCodeSessionId: value.currentCodeSessionId,
    queryGeneration: value.queryGeneration,
    historicProvenance: 'unknown',
    queryToOsAssociation: 'unknown',
    reportBasis:
      'manager-retained-report; not independent OS association',
  };
}

function sameNodeState(left, right) {
  return (
    left.dev === right.dev &&
    left.ino === right.ino &&
    left.mode === right.mode &&
    left.uid === right.uid &&
    left.gid === right.gid
  );
}

function sameFileState(left, right) {
  return (
    sameNodeState(left, right) &&
    left.size === right.size &&
    left.mtimeNs === right.mtimeNs &&
    left.ctimeNs === right.ctimeNs
  );
}

function reportsMatchBinding(sample) {
  const binding = sample?.binding;
  const before = normalizeReport(
    sample?.observation?.fields?.hostBefore?.value
      ?.selectedExecutorReport,
  );
  const after = normalizeReport(
    sample?.observation?.fields?.hostAfter?.value
      ?.selectedExecutorReport,
  );

  if (
    !isPlainObject(binding) ||
    !before ||
    !after ||
    before.cliPid === null ||
    JSON.stringify(before) !== JSON.stringify(after) ||
    before.taskId !== binding.targetTaskId ||
    before.currentCodeSessionId !==
      binding.targetCodeSessionId ||
    before.queryGeneration !== binding.queryGeneration
  ) {
    return null;
  }

  return before;
}

function selectSample(acquisition) {
  if (
    !isPlainObject(acquisition) ||
    acquisition.state !== 'usable-partial' ||
    acquisition.qualification !== 'unqualified' ||
    !isPlainObject(acquisition.sample)
  ) {
    return null;
  }

  const report = reportsMatchBinding(acquisition.sample);
  if (!report) return null;

  return {
    sample: acquisition.sample,
    report,
    fingerprint: JSON.stringify(acquisition.sample),
  };
}

function sampleEvidence(sample) {
  return {
    binding: { ...sample.binding },
    sequence: sample.sequence,
    observedAt: sample.observedAt,
    collection: {
      startedAt: sample.observation.collection.startedAt,
      endedAt: sample.observation.collection.endedAt,
    },
  };
}

function validateExecutableState(state) {
  if (
    !state.isFile() ||
    state.size < 1n ||
    state.size > BigInt(MAX_EXECUTABLE_BYTES)
  ) {
    throw new Error('unavailable executable');
  }

  return state;
}

export function createSelectedLinuxExecutorObserver({
  processRoot,
  readProbeSample,
  lstat,
  open,
  constants = fsConstants,
  getuid,
  now,
}) {
  if (
    typeof processRoot !== 'string' ||
    !isAbsolute(processRoot) ||
    typeof readProbeSample !== 'function' ||
    typeof lstat !== 'function' ||
    typeof open !== 'function' ||
    typeof getuid !== 'function' ||
    typeof now !== 'function'
  ) {
    throw new TypeError('invalid selected executor I/O seam');
  }

  async function readOwnedProcessDirectory(
    path,
    expectedUid,
  ) {
    const state = await lstat(path, { bigint: true });

    if (
      !state.isDirectory() ||
      state.isSymbolicLink() ||
      state.uid !== expectedUid
    ) {
      throw new Error('unavailable process directory');
    }

    return state;
  }

  async function readStartTicks(path, expectedPid) {
    let handle;

    try {
      handle = await open(
        path,
        constants.O_RDONLY | constants.O_NOFOLLOW,
      );

      const before = await handle.stat({ bigint: true });

      if (!before.isFile()) {
        throw new Error('unavailable process stat');
      }

      const buffer = Buffer.alloc(MAX_STAT_BYTES + 1);
      const { bytesRead } = await handle.read(
        buffer,
        0,
        buffer.length,
        0,
      );

      if (bytesRead < 1 || bytesRead > MAX_STAT_BYTES) {
        throw new Error('unavailable process stat');
      }

      const after = await handle.stat({ bigint: true });
      const pathState = await lstat(path, { bigint: true });

      if (
        !sameFileState(before, after) ||
        pathState.isSymbolicLink() ||
        !pathState.isFile() ||
        !sameFileState(after, pathState)
      ) {
        throw new Error('changing process stat');
      }

      const text = new TextDecoder('utf-8', { fatal: true })
        .decode(buffer.subarray(0, bytesRead))
        .trim();

      if (
        text.includes('\n') ||
        text.includes('\r') ||
        !text.startsWith(`${expectedPid} (`)
      ) {
        throw new Error('invalid process stat');
      }

      const commandEnd = text.lastIndexOf(') ');

      if (commandEnd < 0) {
        throw new Error('invalid process stat');
      }

      const fields = text.slice(commandEnd + 2).split(/\s+/u);
      const processStartTicks = fields[19];

      if (!/^[0-9]+$/u.test(processStartTicks ?? '')) {
        throw new Error('invalid process stat');
      }

      return processStartTicks;
    } finally {
      await handle?.close().catch(() => {});
    }
  }

  async function hashExecutable(path) {
    let handle;

    try {
      // The fixed selected PID's /proc executable entry is followed.
      handle = await open(path, constants.O_RDONLY);
      const before = validateExecutableState(
        await handle.stat({ bigint: true }),
      );
      const size = Number(before.size);
      const buffer = Buffer.allocUnsafe(HASH_BUFFER_BYTES);
      const hash = createHash('sha256');
      let position = 0;

      while (position < size) {
        const length = Math.min(
          buffer.length,
          size - position,
        );
        const { bytesRead } = await handle.read(
          buffer,
          0,
          length,
          position,
        );

        if (bytesRead < 1) {
          throw new Error('unavailable executable');
        }

        hash.update(buffer.subarray(0, bytesRead));
        position += bytesRead;
      }

      const after = validateExecutableState(
        await handle.stat({ bigint: true }),
      );

      if (!sameFileState(before, after)) {
        throw new Error('changing executable');
      }

      return {
        state: after,
        sha256: hash.digest('hex'),
      };
    } finally {
      await handle?.close().catch(() => {});
    }
  }

  async function readExecutableState(path) {
    let handle;

    try {
      handle = await open(path, constants.O_RDONLY);
      return validateExecutableState(
        await handle.stat({ bigint: true }),
      );
    } finally {
      await handle?.close().catch(() => {});
    }
  }

  async function acquire(input) {
    return readProbeSample({
      runDirectory: input.runDirectory,
      sequence: input.sequence,
      expectedBinding: input.expectedBinding,
      now: now(),
      afterSequence: input.afterSequence,
      maximumAgeMs: input.maximumAgeMs,
    });
  }

  return async function observeSelectedLinuxExecutor(input) {
    if (
      !isPlainObject(input) ||
      typeof getuid() !== 'number' ||
      !Number.isSafeInteger(input.expectedUid) ||
      input.expectedUid < 0 ||
      input.expectedUid !== getuid()
    ) {
      return unknownSample();
    }

    const expectedUid = BigInt(input.expectedUid);
    const selected = selectSample(await acquire(input));

    if (!selected) return unknownSample();

    const processDirectory = join(
      processRoot,
      String(selected.report.cliPid),
    );
    const statPath = join(processDirectory, 'stat');
    const executablePath = join(processDirectory, 'exe');

    try {
      const processBefore = await readOwnedProcessDirectory(
        processDirectory,
        expectedUid,
      );
      const startBefore = await readStartTicks(
        statPath,
        selected.report.cliPid,
      );

      const processBeforeHash =
        await readOwnedProcessDirectory(
          processDirectory,
          expectedUid,
        );
      const executable = await hashExecutable(executablePath);

      const processAfterHash =
        await readOwnedProcessDirectory(
          processDirectory,
          expectedUid,
        );
      const startAfterHash = await readStartTicks(
        statPath,
        selected.report.cliPid,
      );

      const processBeforeReopen =
        await readOwnedProcessDirectory(
          processDirectory,
          expectedUid,
        );
      const executableAfter =
        await readExecutableState(executablePath);

      const processAfterReopen =
        await readOwnedProcessDirectory(
          processDirectory,
          expectedUid,
        );
      const startAfterReopen = await readStartTicks(
        statPath,
        selected.report.cliPid,
      );

      const processAfterAllReads =
        await readOwnedProcessDirectory(
          processDirectory,
          expectedUid,
        );

      if (
        !sameNodeState(processBefore, processBeforeHash) ||
        !sameNodeState(processBeforeHash, processAfterHash) ||
        !sameNodeState(
          processAfterHash,
          processBeforeReopen,
        ) ||
        !sameNodeState(
          processBeforeReopen,
          processAfterReopen,
        ) ||
        !sameNodeState(
          processAfterReopen,
          processAfterAllReads,
        ) ||
        startBefore !== startAfterHash ||
        startAfterHash !== startAfterReopen ||
        !sameFileState(executable.state, executableAfter)
      ) {
        return unknownLinuxIdentity();
      }

      const revalidated = selectSample(await acquire(input));

      if (
        !revalidated ||
        revalidated.fingerprint !== selected.fingerprint ||
        JSON.stringify(revalidated.report) !==
          JSON.stringify(selected.report)
      ) {
        return unknownSample();
      }

      return {
        state: 'observed-partial',
        qualification: 'unqualified',
        sampleEvidence: sampleEvidence(revalidated.sample),
        selectedReport: revalidated.report,
        linuxIdentity: {
          pid: revalidated.report.cliPid,
          processStartTicks: startAfterReopen,
          ownerUid: Number(processAfterAllReads.uid),
          executable: {
            dev: String(executableAfter.dev),
            ino: String(executableAfter.ino),
            size: String(executableAfter.size),
            sha256: executable.sha256,
          },
        },
        queryToOsAssociation: 'unknown',
      };
    } catch {
      return unknownLinuxIdentity();
    }
  };
}
