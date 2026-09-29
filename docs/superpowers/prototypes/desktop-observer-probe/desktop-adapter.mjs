import { createHash } from 'node:crypto';
import { constants } from 'node:fs';
import {
  lstat,
  open,
  readFile,
  realpath,
} from 'node:fs/promises';
import {
  isAbsolute,
  join,
  relative,
  sep,
} from 'node:path';

import {
  attachProbe,
  projectApprovedHost,
} from './observer-probe.mjs';

const MAX_CONFIG_BYTES = 4096;
const MAX_MODULE_BYTES = 256 * 1024;
const ARM_DEADLINE_MS = 60_000;
const MIN_SAMPLE_INTERVAL_MS = 5_000;
const MAX_SAMPLES = 3;

const managerScopes = new WeakMap();
const recordStates = new WeakMap();
const bootingManagers = new WeakSet();

const delay = milliseconds =>
  new Promise(resolve => setTimeout(resolve, milliseconds));

const monotonicMilliseconds = () =>
  Number(process.hrtime.bigint() / 1_000_000n);

function sameFileState(before, after) {
  return (
    before.dev === after.dev &&
    before.ino === after.ino &&
    before.size === after.size &&
    before.mtimeMs === after.mtimeMs &&
    before.ctimeMs === after.ctimeMs
  );
}

function pathIsWithin(parent, child) {
  const delta = relative(parent, child);

  return (
    delta === '' ||
    (
      delta !== '..' &&
      !delta.startsWith(`..${sep}`) &&
      !isAbsolute(delta)
    )
  );
}

async function readPrivateConfig(path, uid) {
  let handle;

  try {
    handle = await open(
      path,
      constants.O_RDONLY | constants.O_NOFOLLOW,
    );

    const before = await handle.stat();

    if (
      !before.isFile() ||
      before.uid !== uid ||
      before.nlink !== 1 ||
      (before.mode & 0o7777) !== 0o600 ||
      before.size < 1 ||
      before.size > MAX_CONFIG_BYTES
    ) {
      throw new Error('invalid observer config');
    }

    const bytes = await handle.readFile();
    const after = await handle.stat();
    const pathState = await lstat(path);

    if (
      !sameFileState(before, after) ||
      pathState.isSymbolicLink() ||
      !pathState.isFile() ||
      !sameFileState(after, pathState)
    ) {
      throw new Error('invalid observer config');
    }

    const text = new TextDecoder('utf-8', { fatal: true }).decode(bytes);
    return {
      value: JSON.parse(text),
      sha256: createHash('sha256').update(bytes).digest('hex'),
    };
  } catch {
    throw new Error('invalid observer config');
  } finally {
    await handle?.close().catch(() => {});
  }
}

async function sha256File(path) {
  let handle;

  try {
    handle = await open(
      path,
      constants.O_RDONLY | constants.O_NOFOLLOW,
    );

    const before = await handle.stat();

    if (!before.isFile() || before.size < 1) {
      throw new Error('invalid observer artifact');
    }

    const hash = createHash('sha256');
    const buffer = Buffer.allocUnsafe(64 * 1024);
    let position = 0;

    while (position < before.size) {
      const length = Math.min(buffer.length, before.size - position);
      const { bytesRead } = await handle.read(
        buffer,
        0,
        length,
        position,
      );

      if (bytesRead < 1) {
        throw new Error('invalid observer artifact');
      }

      hash.update(buffer.subarray(0, bytesRead));
      position += bytesRead;
    }

    const after = await handle.stat();
    const pathState = await lstat(path);

    if (
      !sameFileState(before, after) ||
      pathState.isSymbolicLink() ||
      !pathState.isFile() ||
      !sameFileState(after, pathState)
    ) {
      throw new Error('invalid observer artifact');
    }

    return hash.digest('hex');
  } finally {
    await handle?.close().catch(() => {});
  }
}

async function sha256PackedModule(path) {
  const before = await lstat(path);

  if (
    before.isSymbolicLink() ||
    !before.isFile() ||
    !Number.isSafeInteger(before.size) ||
    before.size < 1 ||
    before.size > MAX_MODULE_BYTES
  ) {
    throw new Error('invalid observer artifact');
  }

  const bytes = await readFile(path);

  if (
    bytes.length !== before.size ||
    bytes.length < 1 ||
    bytes.length > MAX_MODULE_BYTES
  ) {
    throw new Error('invalid observer artifact');
  }

  const after = await lstat(path);

  // Electron synthesizes inode and timestamp metadata for packed ASAR
  // members. The member kind and declared size are the stable properties
  // available here; the physical archive is verified around this read.
  if (
    after.isSymbolicLink() ||
    !after.isFile() ||
    after.size !== before.size
  ) {
    throw new Error('invalid observer artifact');
  }

  return createHash('sha256').update(bytes).digest('hex');
}

async function readProcessStartTicks() {
  let handle;

  try {
    handle = await open(
      '/proc/self/stat',
      constants.O_RDONLY | constants.O_NOFOLLOW,
    );

    const buffer = Buffer.alloc(4097);
    const { bytesRead } = await handle.read(
      buffer,
      0,
      buffer.length,
      0,
    );

    if (bytesRead < 1 || bytesRead === buffer.length) {
      throw new Error('invalid process identity');
    }

    const text = new TextDecoder('utf-8', { fatal: true })
      .decode(buffer.subarray(0, bytesRead))
      .trim();

    if (!text.startsWith(`${process.pid} (`)) {
      throw new Error('invalid process identity');
    }

    const commandEnd = text.lastIndexOf(') ');

    if (commandEnd < 0) {
      throw new Error('invalid process identity');
    }

    const fields = text.slice(commandEnd + 2).split(/\s+/u);
    const processStartTicks = fields[19];

    if (!/^[0-9]+$/u.test(processStartTicks ?? '')) {
      throw new Error('invalid process identity');
    }

    return processStartTicks;
  } finally {
    await handle?.close().catch(() => {});
  }
}

function stateOf(record) {
  let state = recordStates.get(record);

  if (!state) {
    state = {
      generation: 1,
      modeEvent: null,
    };
    recordStates.set(record, state);
  }

  return state;
}

function selectedRecord(manager, subject) {
  const scope = managerScopes.get(manager);

  if (!scope) return null;

  let record;

  if (
    subject !== null &&
    (typeof subject === 'object' || typeof subject === 'function')
  ) {
    record = subject;
  } else {
    if (subject !== scope.targetTaskId) return null;
    record = manager.sessions.get(scope.targetTaskId);
  }

  return record?.sessionId === scope.targetTaskId ? record : null;
}

function bumpGeneration(record) {
  const state = stateOf(record);
  state.generation += 1;
  state.modeEvent = null;
  return state.generation;
}

function projectHost(manager, record, state, dependencies) {
  const route = manager.cliOAuthTokenKeeper?.spawnAccountOf(record);
  const requests = record.permissionModeRequestsInFlight;

  return {
    spawnRoute:
      route === undefined || route === null
        ? undefined
        : {
            accountUuid: route.accountUuid,
            orgId: route.orgId,
          },
    permissionMode: record.permissionMode,
    modeEvent:
      state.modeEvent?.generation === state.generation &&
      state.modeEvent.query === record.query
        ? {
            mode: state.modeEvent.mode,
            at: state.modeEvent.at,
            generation: state.modeEvent.generation,
          }
        : undefined,
    selectedExecutorReport: {
      taskId: record.sessionId,
      cliPid: record.cliPid,
      cliPidAtMs: record.cliPidAtMs,
      cliReportedVersion: record.cliReportedVersion,
      currentCodeSessionId: record.cliSessionId,
    },
    harnessCwd: record.harnessCwd,
    alwaysAllowedReasons:
      record.alwaysAllowedReasons === undefined
        ? undefined
        : Array.from(record.alwaysAllowedReasons),
    cuAllowedApps: record.cuAllowedApps,
    cuGrantFlags: record.cuGrantFlags,
    effectiveCuAllowedApps:
      dependencies.effectiveCuAllowedApps(record),
    effectiveCuGrantFlags:
      dependencies.effectiveCuGrantFlags(record),
    sessionPermissionUpdates: record.sessionPermissionUpdates,
    flagScopeSyncPending: record.flagScopeSyncPending,
    modeRequestsInFlight:
      requests?.query === record.query
        ? requests.count
        : undefined,
  };
}

export function createDesktopAdapter({
  manager,
  targetTaskId,
  isUnavailable,
  effectiveCuAllowedApps,
  effectiveCuGrantFlags,
  now = Date.now,
}) {
  if (
    !manager ||
    typeof manager !== 'object' ||
    typeof manager.sessions?.get !== 'function' ||
    typeof targetTaskId !== 'string' ||
    targetTaskId.length === 0 ||
    typeof isUnavailable !== 'function' ||
    typeof effectiveCuAllowedApps !== 'function' ||
    typeof effectiveCuGrantFlags !== 'function' ||
    typeof now !== 'function'
  ) {
    throw new Error('invalid Desktop adapter');
  }

  const scope = { targetTaskId, now };
  const views = new WeakMap();

  managerScopes.set(manager, scope);

  const selectReceiver = requestedTaskId => {
    try {
      if (requestedTaskId !== targetTaskId) return null;

      const record = manager.sessions.get(targetTaskId);

      if (
        !record ||
        record.sessionId !== targetTaskId ||
        isUnavailable(record)
      ) {
        return null;
      }

      let view = views.get(record);

      if (!view) {
        const state = stateOf(record);

        view = Object.freeze({
          get taskId() {
            return record.sessionId;
          },
          get codeSessionId() {
            return record.cliSessionId;
          },
          get query() {
            return record.query;
          },
          get inputStream() {
            return record.inputStream;
          },
          get generation() {
            return state.generation;
          },
          get host() {
            return projectHost(manager, record, state, {
              effectiveCuAllowedApps,
              effectiveCuGrantFlags,
            });
          },
        });

        views.set(record, view);
      }

      return view;
    } catch {
      return null;
    }
  };

  return Object.freeze({
    selectReceiver,
    dispose() {
      if (managerScopes.get(manager) === scope) {
        managerScopes.delete(manager);
      }
    },
  });
}

export function noteQueryInstalled(manager, subject) {
  try {
    const record = selectedRecord(manager, subject);
    if (!record) return false;
    bumpGeneration(record);
    return true;
  } catch {
    return false;
  }
}

export function teardownQuery(manager, subject) {
  try {
    const record = selectedRecord(manager, subject);
    if (!record) return false;
    bumpGeneration(record);
    return true;
  } catch {
    return false;
  }
}

export function noteCodeSessionId(manager, record, nextCodeSessionId) {
  try {
    const selected = selectedRecord(manager, record);

    if (!selected || selected.cliSessionId === nextCodeSessionId) {
      return false;
    }

    bumpGeneration(selected);
    return true;
  } catch {
    return false;
  }
}

export function recordModeEvent(manager, record, query, mode) {
  try {
    const scope = managerScopes.get(manager);
    const selected = selectedRecord(manager, record);

    if (!scope || !selected || selected.query !== query) {
      return false;
    }

    const at = scope.now();

    if (!Number.isSafeInteger(at) || at < 0) {
      return false;
    }

    const state = stateOf(selected);

    state.modeEvent = {
      mode,
      at,
      generation: state.generation,
      query,
    };

    return true;
  } catch {
    return false;
  }
}

async function waitForArm(probe, config) {
  const armPath = join(config.runDirectory, 'arm.json');
  const deadline = monotonicMilliseconds() + ARM_DEADLINE_MS;

  while (monotonicMilliseconds() < deadline) {
    try {
      await lstat(armPath);
      await probe.acceptArm();
      return true;
    } catch (error) {
      if (error?.code !== 'ENOENT') throw error;
    }

    const remaining = deadline - monotonicMilliseconds();

    if (remaining <= 0) break;
    await delay(Math.min(config.pollIntervalMs, remaining));
  }

  return false;
}

async function collectSamples(probe) {
  for (
    let count = 0;
    count < MAX_SAMPLES && probe.state === 'armed';
    count += 1
  ) {
    await delay(MIN_SAMPLE_INTERVAL_MS);

    if (probe.state !== 'armed') return;

    const result = await probe.sample();

    if (result.result !== 'complete' || probe.state === 'terminal') {
      return;
    }
  }
}

async function runDesktopObserver({
  manager,
  isUnavailable,
  effectiveCuAllowedApps,
  effectiveCuGrantFlags,
  modulePath,
  copiedAsarPath,
  configPath,
}) {
  if (
    !isAbsolute(configPath) ||
    !isAbsolute(modulePath) ||
    !isAbsolute(copiedAsarPath) ||
    typeof process.getuid !== 'function'
  ) {
    throw new Error('invalid observer bootstrap');
  }

  const uid = process.getuid();
  const suppliedPathState = await lstat(configPath);

  if (suppliedPathState.isSymbolicLink()) {
    throw new Error('invalid observer config');
  }

  const selectedConfigPath = await realpath(configPath);
  const initialConfig = await readPrivateConfig(selectedConfigPath, uid);
  const config = initialConfig.value;

  if (
    typeof config?.runDirectory !== 'string' ||
    !isAbsolute(config.runDirectory)
  ) {
    throw new Error('invalid observer config');
  }

  const realRunDirectory = await realpath(config.runDirectory);

  if (pathIsWithin(realRunDirectory, selectedConfigPath)) {
    throw new Error('observer config is inside run directory');
  }

  const copiedAsarSha256Before = await sha256File(copiedAsarPath);

  if (copiedAsarSha256Before !== config.copiedAsarSha256) {
    throw new Error('copied archive identity mismatch');
  }

  const moduleSha256 = await sha256PackedModule(modulePath);

  if (moduleSha256 !== config.moduleSha256) {
    throw new Error('observer module identity mismatch');
  }

  const copiedAsarSha256After = await sha256File(copiedAsarPath);

  if (
    copiedAsarSha256After !== copiedAsarSha256Before ||
    copiedAsarSha256After !== config.copiedAsarSha256
  ) {
    throw new Error('copied archive identity mismatch');
  }

  const confirmedConfig = await readPrivateConfig(selectedConfigPath, uid);

  if (confirmedConfig.sha256 !== initialConfig.sha256) {
    throw new Error('invalid observer config');
  }

  const processIdentity = {
    pid: process.pid,
    processStartTicks: await readProcessStartTicks(),
    uid,
  };

  const adapter = createDesktopAdapter({
    manager,
    targetTaskId: config.targetTaskId,
    isUnavailable,
    effectiveCuAllowedApps,
    effectiveCuGrantFlags,
  });

  try {
    const probe = await attachProbe({
      config,
      selectReceiver: adapter.selectReceiver,
      approvedHostProjection: projectApprovedHost,
      processIdentity,
    });

    if (await waitForArm(probe, config)) {
      await collectSamples(probe);
    }
  } finally {
    adapter.dispose();
  }
}

export function bootDesktopObserver({
  manager,
  isUnavailable,
  effectiveCuAllowedApps,
  effectiveCuGrantFlags,
  modulePath,
  copiedAsarPath,
}) {
  try {
    const configPath = process.env.PROVINGKIT_OBSERVER_CONFIG;

    if (
      typeof configPath !== 'string' ||
      configPath.length === 0 ||
      bootingManagers.has(manager)
    ) {
      return false;
    }

    bootingManagers.add(manager);

    return runDesktopObserver({
      manager,
      isUnavailable,
      effectiveCuAllowedApps,
      effectiveCuGrantFlags,
      modulePath,
      copiedAsarPath,
      configPath,
    }).then(
      () => true,
      () => false,
    );
  } catch {
    return false;
  }
}
