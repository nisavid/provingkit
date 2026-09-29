import { createHash } from 'node:crypto';
import { constants as fsConstants } from 'node:fs';
import {
  isAbsolute,
  join,
} from 'node:path';
import { TextDecoder } from 'node:util';

import {
  MAX_CWD_BYTES,
  MAX_OBSERVATION_WINDOW_MS,
  MAX_SAMPLES,
  MONOTONIC_CLOCK_ID,
  SELECTED_EXECUTOR_REPORT_BASIS,
  SELECTED_EXECUTOR_REPORT_KEYS,
} from './observer-contract.mjs';
import { isValidProbeBinding } from './probe-reader.mjs';

const MAX_STAT_BYTES = 4096;
const MAX_EXECUTABLE_BYTES = 256 * 1024 * 1024;
const HASH_BUFFER_BYTES = 64 * 1024;
const MAX_TEXT_BYTES = 256;
const PROCESS_DESCRIPTOR_ROOT = '/proc/self/fd';
const SELECTED_EXECUTOR_INPUT_KEYS = Object.freeze([
  'afterSequence',
  'expectedBinding',
  'expectedUid',
  'maximumAgeMs',
  'runDirectory',
  'sequence',
]);

class StaleSelectedSampleError extends Error {}

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
    !hasExactKeys(value, SELECTED_EXECUTOR_REPORT_KEYS) ||
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
    value.reportBasis !== SELECTED_EXECUTOR_REPORT_BASIS
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
    reportBasis: SELECTED_EXECUTOR_REPORT_BASIS,
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
    observedAtMonotonicMs: sample.observedAtMonotonicMs,
    collection: {
      startedAt: sample.observation.collection.startedAt,
      endedAt: sample.observation.collection.endedAt,
      startedAtMonotonicMs:
        sample.observation.collection.startedAtMonotonicMs,
      endedAtMonotonicMs:
        sample.observation.collection.endedAtMonotonicMs,
    },
  };
}

function isFreshAt(
  sample,
  maximumAgeMs,
  wallNow,
  monotonicNow,
) {
  const collection = sample?.observation?.collection;
  const values = [
    maximumAgeMs,
    wallNow,
    monotonicNow,
    sample?.observedAt,
    sample?.observedAtMonotonicMs,
    collection?.endedAt,
    collection?.endedAtMonotonicMs,
  ];

  if (
    !values.every(
      value =>
        Number.isSafeInteger(value) && value >= 0,
    ) ||
    maximumAgeMs < 1 ||
    maximumAgeMs > MAX_OBSERVATION_WINDOW_MS
  ) {
    return false;
  }

  return (
    wallNow >= sample.observedAt &&
    wallNow >= collection.endedAt &&
    monotonicNow >= sample.observedAtMonotonicMs &&
    monotonicNow >= collection.endedAtMonotonicMs &&
    wallNow - sample.observedAt <= maximumAgeMs &&
    monotonicNow - sample.observedAtMonotonicMs <=
      maximumAgeMs
  );
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

function descriptorChildPath(directoryHandle, childName) {
  if (
    !Number.isSafeInteger(directoryHandle?.fd) ||
    directoryHandle.fd < 0 ||
    (childName !== 'stat' && childName !== 'exe')
  ) {
    throw new Error('invalid process descriptor');
  }

  return join(
    PROCESS_DESCRIPTOR_ROOT,
    String(directoryHandle.fd),
    childName,
  );
}

function snapshotObservationInput(input, currentUid) {
  if (!hasExactKeys(input, SELECTED_EXECUTOR_INPUT_KEYS)) {
    return null;
  }

  const expectedBinding = isPlainObject(input.expectedBinding)
    ? { ...input.expectedBinding }
    : input.expectedBinding;
  const snapshot = {
    afterSequence: input.afterSequence,
    expectedBinding,
    expectedUid: input.expectedUid,
    maximumAgeMs: input.maximumAgeMs,
    runDirectory: input.runDirectory,
    sequence: input.sequence,
  };

  if (
    !Number.isSafeInteger(currentUid) ||
    currentUid < 0 ||
    !Number.isSafeInteger(snapshot.expectedUid) ||
    snapshot.expectedUid < 0 ||
    snapshot.expectedUid !== currentUid ||
    typeof snapshot.runDirectory !== 'string' ||
    !isAbsolute(snapshot.runDirectory) ||
    hasControlCharacters(snapshot.runDirectory) ||
    Buffer.byteLength(snapshot.runDirectory, 'utf8') >
      MAX_CWD_BYTES ||
    !Number.isSafeInteger(snapshot.sequence) ||
    snapshot.sequence < 1 ||
    snapshot.sequence > MAX_SAMPLES ||
    !Number.isSafeInteger(snapshot.afterSequence) ||
    snapshot.afterSequence !== snapshot.sequence - 1 ||
    !Number.isSafeInteger(snapshot.maximumAgeMs) ||
    snapshot.maximumAgeMs < 1 ||
    snapshot.maximumAgeMs > MAX_OBSERVATION_WINDOW_MS ||
    !isValidProbeBinding(snapshot.expectedBinding)
  ) {
    return null;
  }

  Object.freeze(snapshot.expectedBinding);
  return Object.freeze(snapshot);
}

export function createSelectedLinuxExecutorObserver({
  processRoot,
  readProbeSample,
  lstat,
  open,
  constants = fsConstants,
  getuid,
  now,
  monotonicNow,
  readLinuxBootId,
}) {
  if (
    typeof processRoot !== 'string' ||
    !isAbsolute(processRoot) ||
    typeof readProbeSample !== 'function' ||
    typeof lstat !== 'function' ||
    typeof open !== 'function' ||
    typeof getuid !== 'function' ||
    typeof now !== 'function' ||
    typeof monotonicNow !== 'function' ||
    typeof readLinuxBootId !== 'function' ||
    !Number.isInteger(constants.O_DIRECTORY) ||
    !Number.isInteger(constants.O_NOFOLLOW)
  ) {
    throw new TypeError('invalid selected executor I/O seam');
  }

  function isFreshNow(sample, maximumAgeMs) {
    try {
      return isFreshAt(
        sample,
        maximumAgeMs,
        now(),
        monotonicNow(),
      );
    } catch {
      return false;
    }
  }

  function requireFresh(sample, maximumAgeMs) {
    if (!isFreshNow(sample, maximumAgeMs)) {
      throw new StaleSelectedSampleError(
        'selected sample expired',
      );
    }
  }

  async function readOwnedProcessDirectoryPath(
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

  function validateBoundProcessDirectory(
    state,
    boundState,
    expectedUid,
  ) {
    if (
      !state.isDirectory() ||
      state.isSymbolicLink() ||
      state.uid !== expectedUid ||
      !sameNodeState(state, boundState)
    ) {
      throw new Error('changed process directory');
    }

    return state;
  }

  async function bindProcessDirectory({
    path,
    expectedUid,
    sample,
    maximumAgeMs,
  }) {
    let handle;

    try {
      const pathBefore =
        await readOwnedProcessDirectoryPath(
          path,
          expectedUid,
        );

      requireFresh(sample, maximumAgeMs);

      handle = await open(
        path,
        constants.O_RDONLY |
          constants.O_DIRECTORY |
          constants.O_NOFOLLOW,
      );

      const descriptorState = validateBoundProcessDirectory(
        await handle.stat({ bigint: true }),
        pathBefore,
        expectedUid,
      );
      const pathAfter =
        await readOwnedProcessDirectoryPath(
          path,
          expectedUid,
        );

      if (!sameNodeState(descriptorState, pathAfter)) {
        throw new Error('changed process directory path');
      }

      return {
        handle,
        state: descriptorState,
      };
    } catch (error) {
      await handle?.close().catch(() => {});
      throw error;
    }
  }

  async function prepareSensitiveOpen({
    directoryHandle,
    boundState,
    expectedUid,
    sample,
    maximumAgeMs,
  }) {
    const state = validateBoundProcessDirectory(
      await directoryHandle.stat({ bigint: true }),
      boundState,
      expectedUid,
    );

    requireFresh(sample, maximumAgeMs);
    return state;
  }

  async function readStartTicks(
    directoryHandle,
    expectedPid,
  ) {
    let handle;

    try {
      handle = await open(
        descriptorChildPath(directoryHandle, 'stat'),
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

      if (
        !sameFileState(before, after)
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

  async function hashExecutable(directoryHandle) {
    let handle;

    try {
      // The bound selected PID directory's executable entry is followed.
      handle = await open(
        descriptorChildPath(directoryHandle, 'exe'),
        constants.O_RDONLY,
      );
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

  async function readExecutableState(directoryHandle) {
    let handle;

    try {
      handle = await open(
        descriptorChildPath(directoryHandle, 'exe'),
        constants.O_RDONLY,
      );
      return validateExecutableState(
        await handle.stat({ bigint: true }),
      );
    } finally {
      await handle?.close().catch(() => {});
    }
  }

  async function acquire(input) {
    const linuxBootId = await readLinuxBootId();
    const acquisitionNow = now();
    const acquisitionMonotonicNow = monotonicNow();
    const acquisition = await readProbeSample({
      runDirectory: input.runDirectory,
      sequence: input.sequence,
      expectedBinding: input.expectedBinding,
      now: acquisitionNow,
      monotonicNow: acquisitionMonotonicNow,
      monotonicClockId: MONOTONIC_CLOCK_ID,
      linuxBootId,
      afterSequence: input.afterSequence,
      maximumAgeMs: input.maximumAgeMs,
    });

    const selected = selectSample(acquisition);

    if (
      !selected ||
      selected.sample.binding.monotonicClockId !==
        MONOTONIC_CLOCK_ID ||
      selected.sample.binding.linuxBootId !== linuxBootId ||
      !isFreshNow(
        selected.sample,
        input.maximumAgeMs,
      )
    ) {
      return null;
    }

    return selected;
  }

  return async function observeSelectedLinuxExecutor(input) {
    let currentUid;

    try {
      currentUid = getuid();
    } catch {
      return unknownSample();
    }

    const inputSnapshot = snapshotObservationInput(
      input,
      currentUid,
    );

    if (!inputSnapshot) return unknownSample();

    const expectedUid = BigInt(inputSnapshot.expectedUid);
    let selected;

    try {
      selected = await acquire(inputSnapshot);
    } catch {
      return unknownSample();
    }

    if (!selected) return unknownSample();

    const processDirectory = join(
      processRoot,
      String(selected.report.cliPid),
    );
    let processDirectoryHandle;

    try {
      const boundProcess = await bindProcessDirectory({
        path: processDirectory,
        expectedUid,
        sample: selected.sample,
        maximumAgeMs: inputSnapshot.maximumAgeMs,
      });
      processDirectoryHandle = boundProcess.handle;

      await prepareSensitiveOpen({
        directoryHandle: processDirectoryHandle,
        boundState: boundProcess.state,
        expectedUid,
        sample: selected.sample,
        maximumAgeMs: inputSnapshot.maximumAgeMs,
      });
      const startBefore = await readStartTicks(
        processDirectoryHandle,
        selected.report.cliPid,
      );

      await prepareSensitiveOpen({
        directoryHandle: processDirectoryHandle,
        boundState: boundProcess.state,
        expectedUid,
        sample: selected.sample,
        maximumAgeMs: inputSnapshot.maximumAgeMs,
      });
      const startBeforeHash = await readStartTicks(
        processDirectoryHandle,
        selected.report.cliPid,
      );

      await prepareSensitiveOpen({
        directoryHandle: processDirectoryHandle,
        boundState: boundProcess.state,
        expectedUid,
        sample: selected.sample,
        maximumAgeMs: inputSnapshot.maximumAgeMs,
      });
      const executable = await hashExecutable(
        processDirectoryHandle,
      );

      await prepareSensitiveOpen({
        directoryHandle: processDirectoryHandle,
        boundState: boundProcess.state,
        expectedUid,
        sample: selected.sample,
        maximumAgeMs: inputSnapshot.maximumAgeMs,
      });
      const startAfterReopen = await readStartTicks(
        processDirectoryHandle,
        selected.report.cliPid,
      );

      const processBeforeReopen =
        await prepareSensitiveOpen({
          directoryHandle: processDirectoryHandle,
          boundState: boundProcess.state,
          expectedUid,
          sample: selected.sample,
          maximumAgeMs: inputSnapshot.maximumAgeMs,
        });
      const executableAfter =
        await readExecutableState(
          processDirectoryHandle,
        );

      const processAfterReopen =
        validateBoundProcessDirectory(
          await processDirectoryHandle.stat({
            bigint: true,
          }),
          boundProcess.state,
          expectedUid,
        );

      if (
        !sameNodeState(
          processBeforeReopen,
          processAfterReopen,
        ) ||
        startBefore !== startBeforeHash ||
        startBeforeHash !== startAfterReopen ||
        !sameFileState(executable.state, executableAfter)
      ) {
        return unknownLinuxIdentity();
      }

      let revalidated;

      try {
        revalidated = await acquire(inputSnapshot);
      } catch {
        return unknownSample();
      }

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
          ownerUid: Number(processAfterReopen.uid),
          executable: {
            dev: String(executableAfter.dev),
            ino: String(executableAfter.ino),
            size: String(executableAfter.size),
            sha256: executable.sha256,
          },
        },
        queryToOsAssociation: 'unknown',
      };
    } catch (error) {
      if (error instanceof StaleSelectedSampleError) {
        return unknownSample();
      }

      return unknownLinuxIdentity();
    } finally {
      await processDirectoryHandle?.close().catch(() => {});
    }
  };
}
