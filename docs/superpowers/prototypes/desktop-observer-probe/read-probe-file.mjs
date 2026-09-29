import { constants } from 'node:fs';
import { lstat, open } from 'node:fs/promises';
import path from 'node:path';
import { TextDecoder } from 'node:util';

import { inspectProbeSample } from './probe-reader.mjs';

const MAX_SAMPLE_BYTES = 16 * 1024;
const MIN_SEQUENCE = 1;
const MAX_SEQUENCE = 3;

const ACQUISITION_FAILURE = Object.freeze({
  state: 'unknown',
  reason: 'sample-unavailable',
  qualification: 'unqualified',
});

const INVALID_SAMPLE = Object.freeze({
  state: 'unknown',
  reason: 'invalid-sample',
  qualification: 'unqualified',
});

const FILE_SNAPSHOT_KEYS = Object.freeze([
  'dev',
  'ino',
  'size',
  'mtimeNs',
  'ctimeNs',
]);

const sameFields = (left, right, keys) =>
  keys.every(key => left[key] === right[key]);

const hasMode = (stat, expected) =>
  (stat.mode & 0o7777n) === expected;

const isSafeDirectory = (stat, uid) =>
  stat.isDirectory() &&
  stat.uid === uid &&
  hasMode(stat, 0o700n);

const isSafeSelectedFile = (stat, uid) =>
  stat.isFile() &&
  stat.uid === uid &&
  hasMode(stat, 0o600n) &&
  stat.nlink === 1n &&
  stat.size >= 1n &&
  stat.size <= BigInt(MAX_SAMPLE_BYTES);

async function closeQuietly(handle) {
  if (!handle) return;

  try {
    await handle.close();
  } catch {
    return;
  }
}

export async function readProbeSample(input) {
  let directoryHandle;
  let fileHandle;

  try {
    if (
      !input ||
      typeof input !== 'object' ||
      typeof process.getuid !== 'function' ||
      !Number.isInteger(constants.O_DIRECTORY) ||
      !Number.isInteger(constants.O_NOFOLLOW)
    ) {
      return ACQUISITION_FAILURE;
    }

    const {
      runDirectory,
      sequence,
      expectedBinding,
      now,
      afterSequence,
      monotonicNow,
      monotonicClockId,
      linuxBootId,
      maximumAgeMs,
    } = input;

    if (
      typeof runDirectory !== 'string' ||
      !path.isAbsolute(runDirectory) ||
      !Number.isSafeInteger(sequence) ||
      sequence < MIN_SEQUENCE ||
      sequence > MAX_SEQUENCE
    ) {
      return ACQUISITION_FAILURE;
    }

    const uid = BigInt(process.getuid());
    const selectedPath = path.join(
      runDirectory,
      `sample-${String(sequence).padStart(6, '0')}.json`,
    );

    const directoryPathBefore = await lstat(runDirectory, {
      bigint: true,
    });

    if (!isSafeDirectory(directoryPathBefore, uid)) {
      return ACQUISITION_FAILURE;
    }

    directoryHandle = await open(
      runDirectory,
      constants.O_RDONLY |
        constants.O_DIRECTORY |
        constants.O_NOFOLLOW,
    );

    const directoryDescriptorBefore = await directoryHandle.stat({
      bigint: true,
    });

    if (
      !isSafeDirectory(directoryDescriptorBefore, uid) ||
      !sameFields(
        directoryPathBefore,
        directoryDescriptorBefore,
        ['dev', 'ino'],
      )
    ) {
      return ACQUISITION_FAILURE;
    }

    const selectedPathBefore = await lstat(selectedPath, {
      bigint: true,
    });

    if (!isSafeSelectedFile(selectedPathBefore, uid)) {
      return ACQUISITION_FAILURE;
    }

    fileHandle = await open(
      selectedPath,
      constants.O_RDONLY | constants.O_NOFOLLOW,
    );

    const selectedDescriptorBefore = await fileHandle.stat({
      bigint: true,
    });

    if (
      !isSafeSelectedFile(selectedDescriptorBefore, uid) ||
      !sameFields(
        selectedPathBefore,
        selectedDescriptorBefore,
        FILE_SNAPSHOT_KEYS,
      )
    ) {
      return ACQUISITION_FAILURE;
    }

    const buffer = Buffer.alloc(MAX_SAMPLE_BYTES + 1);
    let total = 0;

    while (total < buffer.length) {
      const { bytesRead } = await fileHandle.read(
        buffer,
        total,
        buffer.length - total,
        total,
      );

      if (bytesRead === 0) break;
      total += bytesRead;
    }

    const selectedDescriptorAfter = await fileHandle.stat({
      bigint: true,
    });
    const selectedPathAfter = await lstat(selectedPath, {
      bigint: true,
    });
    const directoryDescriptorAfter = await directoryHandle.stat({
      bigint: true,
    });
    const directoryPathAfter = await lstat(runDirectory, {
      bigint: true,
    });

    if (
      total > MAX_SAMPLE_BYTES ||
      BigInt(total) !== selectedDescriptorBefore.size ||
      !isSafeSelectedFile(selectedDescriptorAfter, uid) ||
      !isSafeSelectedFile(selectedPathAfter, uid) ||
      !sameFields(
        selectedPathBefore,
        selectedDescriptorAfter,
        FILE_SNAPSHOT_KEYS,
      ) ||
      !sameFields(
        selectedPathBefore,
        selectedPathAfter,
        FILE_SNAPSHOT_KEYS,
      ) ||
      !isSafeDirectory(directoryDescriptorAfter, uid) ||
      !isSafeDirectory(directoryPathAfter, uid) ||
      !sameFields(
        directoryDescriptorBefore,
        directoryDescriptorAfter,
        ['dev', 'ino'],
      ) ||
      !sameFields(
        directoryDescriptorBefore,
        directoryPathAfter,
        ['dev', 'ino'],
      )
    ) {
      return ACQUISITION_FAILURE;
    }

    const serialized = new TextDecoder('utf-8', {
      fatal: true,
    }).decode(buffer.subarray(0, total));

    const result = inspectProbeSample(serialized, expectedBinding, {
      now,
      afterSequence,
      monotonicNow,
      monotonicClockId,
      linuxBootId,
      maximumAgeMs,
    });

    if (
      'sample' in result &&
      result.sample.sequence !== sequence
    ) {
      return INVALID_SAMPLE;
    }

    return result;
  } catch {
    return ACQUISITION_FAILURE;
  } finally {
    await closeQuietly(fileHandle);
    await closeQuietly(directoryHandle);
  }
}
