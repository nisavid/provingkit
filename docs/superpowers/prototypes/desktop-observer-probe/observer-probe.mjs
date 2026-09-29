import { createHash, randomBytes } from 'node:crypto';
import { constants } from 'node:fs';
import {
  link,
  lstat,
  open,
  readdir,
  unlink,
} from 'node:fs/promises';
import { isAbsolute, join } from 'node:path';

export const GETTER_SET_ID =
  'desktop-query.readonly.v1:accountInfo,getContextUsage-summary,listPermissionRules';

export const CONFIG_SCHEMA = 'desktop-observer.probe-config.v1';
export const BOOTSTRAP_SCHEMA = 'desktop-observer.bootstrap.v1';
export const ARM_SCHEMA = 'desktop-observer.arm.v1';
export const SAMPLE_SCHEMA = 'desktop-observer.sample.v1';

const MAX_CONFIG_BYTES = 4096;
const MAX_SAMPLE_BYTES = 16 * 1024;
const MAX_RUN_OUTPUT_BYTES = 64 * 1024;
const MAX_SAMPLES = 3;
const MAX_OBSERVATION_WINDOW_MS = 30_000;
const MIN_SAMPLE_INTERVAL_MS = 5_000;
const MAX_GETTER_TIMEOUT_MS = 2_000;
const MAX_SETUP_DEADLINE_MS = 60_000;
const ARM_DEADLINE_MS = 60_000;
const MAX_ARRAY_ITEMS = 32;
const MAX_TEXT_BYTES = 256;
const MAX_CWD_BYTES = 1024;

const UNKNOWN_CLAIMS = Object.freeze([
  'current-account-route',
  'current-model-freshness',
  'current-permission-mode',
  'complete-applied-permissions',
  'current-cwd',
  'native-address-binding',
  'external-delivery-and-ack',
]);

const BINDING_KEYS = Object.freeze([
  'runId',
  'configSha256',
  'moduleSha256',
  'copiedAsarSha256',
  'appStartNonce',
  'pid',
  'processStartTicks',
  'targetTaskId',
  'targetCodeSessionId',
  'queryGeneration',
  'getterSetId',
]);

const ARM_KEYS = Object.freeze([
  'schema',
  ...BINDING_KEYS,
  'maxSamples',
  'minIntervalMs',
  'observationWindowMs',
  'perGetterTimeoutMs',
]);

const HOST_KEYS = Object.freeze([
  'spawnRoute',
  'permissionMode',
  'modeEvent',
  'selectedExecutorReport',
  'harnessCwd',
  'cwdEventProvenance',
  'alwaysAllowedReasons',
  'cuAllowedApps',
  'cuGrantFlags',
  'effectiveCuAllowedApps',
  'effectiveCuGrantFlags',
  'sessionPermissionUpdateTypes',
  'flagScopeSyncPending',
  'modeRequestsInFlight',
  'pendingCoverage',
]);

class DataFault extends Error {
  constructor(kind) {
    super(kind);
    this.kind = kind;
  }
}

const invalid = message => {
  throw new Error(message);
};

const isPlainObject = value => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
};

function exactKeys(value, keys, failure = () => invalid('invalid keys')) {
  if (!isPlainObject(value)) failure();

  const actual = Object.keys(value).sort();
  const expected = [...keys].sort();

  if (
    actual.length !== expected.length ||
    actual.some((key, index) => key !== expected[index])
  ) {
    failure();
  }
}

const canonicalize = value => {
  if (Array.isArray(value)) return value.map(canonicalize);

  if (isPlainObject(value)) {
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map(key => [key, canonicalize(value[key])]),
    );
  }

  return value;
};

const sha256 = value =>
  createHash('sha256').update(value).digest('hex');

const hasControlCharacters = value => /[\u0000-\u001f\u007f]/u.test(value);

const utf8Length = value => Buffer.byteLength(value, 'utf8');

function configText(value, name, maximum = MAX_TEXT_BYTES) {
  if (
    typeof value !== 'string' ||
    value.length === 0 ||
    hasControlCharacters(value) ||
    utf8Length(value) > maximum
  ) {
    invalid(`invalid ${name}`);
  }

  return value;
}

function projectedText(value, maximum = MAX_TEXT_BYTES) {
  if (typeof value !== 'string' || value.length === 0) {
    throw new DataFault('shape_invalid');
  }

  if (hasControlCharacters(value)) {
    throw new DataFault('shape_invalid');
  }

  if (utf8Length(value) > maximum) {
    throw new DataFault('limit_exceeded');
  }

  return value;
}

function projectedBoolean(value) {
  if (typeof value !== 'boolean') {
    throw new DataFault('shape_invalid');
  }

  return value;
}

function projectedNumber(value) {
  if (!Number.isFinite(value) || value < 0) {
    throw new DataFault('shape_invalid');
  }

  return value;
}

function projectedCount(value) {
  if (!Number.isSafeInteger(value) || value < 0) {
    throw new DataFault('shape_invalid');
  }

  return value;
}

function projectedArray(value, projector) {
  if (!Array.isArray(value)) {
    throw new DataFault('shape_invalid');
  }

  if (value.length > MAX_ARRAY_ITEMS) {
    throw new DataFault('limit_exceeded');
  }

  return value.map(projector);
}

function optionalStringArray(value) {
  if (value === undefined) return null;
  return projectedArray(value, item => projectedText(item));
}

function optionalApps(value) {
  if (value === undefined) return null;

  return projectedArray(value, item => ({
    bundleId: projectedText(item?.bundleId),
    grantedAt: projectedNumber(item?.grantedAt),
  }));
}

function optionalFlags(value) {
  if (value === undefined) return null;
  if (!isPlainObject(value)) throw new DataFault('shape_invalid');

  const result = {};

  for (const key of [
    'clipboardRead',
    'clipboardWrite',
    'systemKeyCombos',
  ]) {
    if (value[key] !== undefined) {
      result[key] = projectedBoolean(value[key]);
    }
  }

  return result;
}

function retainedText(value, maximum = MAX_TEXT_BYTES) {
  if (value === undefined || value === null) return null;

  try {
    return projectedText(value, maximum);
  } catch {
    return null;
  }
}

function retainedPositiveInteger(value) {
  return Number.isSafeInteger(value) && value > 0
    ? value
    : null;
}

function retainedTimestamp(value) {
  return Number.isSafeInteger(value) && value >= 0
    ? value
    : null;
}

function validateConfig(input) {
  exactKeys(input, [
    'schema',
    'runDirectory',
    'runId',
    'targetTaskId',
    'targetCodeSessionId',
    'getterSetId',
    'moduleSha256',
    'copiedAsarSha256',
    'setupDeadlineMs',
    'pollIntervalMs',
  ]);

  if (input.schema !== CONFIG_SCHEMA) invalid('invalid config schema');

  const runDirectory = configText(
    input.runDirectory,
    'run directory',
    MAX_CWD_BYTES,
  );

  if (!isAbsolute(runDirectory)) invalid('run directory must be absolute');

  const runId = configText(input.runId, 'run ID');
  const targetTaskId = configText(input.targetTaskId, 'target task ID');
  const targetCodeSessionId = configText(
    input.targetCodeSessionId,
    'target Code session ID',
  );

  if (input.getterSetId !== GETTER_SET_ID) {
    invalid('invalid getter set');
  }

  for (const key of ['moduleSha256', 'copiedAsarSha256']) {
    if (!/^[a-f0-9]{64}$/u.test(input[key])) {
      invalid(`invalid ${key}`);
    }
  }

  if (
    !Number.isSafeInteger(input.setupDeadlineMs) ||
    input.setupDeadlineMs < 1 ||
    input.setupDeadlineMs > MAX_SETUP_DEADLINE_MS
  ) {
    invalid('invalid setup deadline');
  }

  if (
    !Number.isSafeInteger(input.pollIntervalMs) ||
    input.pollIntervalMs < 1 ||
    input.pollIntervalMs > 1000 ||
    input.pollIntervalMs > input.setupDeadlineMs
  ) {
    invalid('invalid poll interval');
  }

  const normalized = {
    schema: CONFIG_SCHEMA,
    runDirectory,
    runId,
    targetTaskId,
    targetCodeSessionId,
    getterSetId: GETTER_SET_ID,
    moduleSha256: input.moduleSha256,
    copiedAsarSha256: input.copiedAsarSha256,
    setupDeadlineMs: input.setupDeadlineMs,
    pollIntervalMs: input.pollIntervalMs,
  };

  const serialized = JSON.stringify(canonicalize(normalized));

  if (Buffer.byteLength(serialized, 'utf8') > MAX_CONFIG_BYTES) {
    invalid('config exceeds size limit');
  }

  return Object.freeze({
    ...normalized,
    configSha256: sha256(serialized),
  });
}

function validateProcessIdentity(input) {
  exactKeys(input, ['pid', 'processStartTicks', 'uid']);

  if (!Number.isSafeInteger(input.pid) || input.pid < 1) {
    invalid('invalid pid');
  }

  if (
    typeof input.processStartTicks !== 'string' ||
    !/^[0-9]+$/u.test(input.processStartTicks)
  ) {
    invalid('invalid process start ticks');
  }

  if (!Number.isSafeInteger(input.uid) || input.uid < 0) {
    invalid('invalid uid');
  }

  return Object.freeze({
    pid: input.pid,
    processStartTicks: input.processStartTicks,
    uid: input.uid,
  });
}

async function assertRunDirectory(runDirectory, uid) {
  const stats = await lstat(runDirectory);

  if (
    !stats.isDirectory() ||
    stats.isSymbolicLink() ||
    stats.uid !== uid ||
    (stats.mode & 0o7777) !== 0o700
  ) {
    invalid('invalid run directory');
  }
}

async function assertEntries(runDirectory, expectedEntries) {
  const actual = (await readdir(runDirectory)).sort();
  const expected = [...expectedEntries].sort();

  if (
    actual.length !== expected.length ||
    actual.some((entry, index) => entry !== expected[index])
  ) {
    invalid('unexpected run directory contents');
  }
}

async function syncDirectory(runDirectory) {
  const directory = await open(
    runDirectory,
    constants.O_RDONLY | constants.O_DIRECTORY,
  );

  try {
    await directory.sync();
  } finally {
    await directory.close();
  }
}

function sameFileState(before, after) {
  return (
    before.dev === after.dev &&
    before.ino === after.ino &&
    before.size === after.size &&
    before.mtimeMs === after.mtimeMs &&
    before.ctimeMs === after.ctimeMs
  );
}

async function readPrivateJson(path, uid, maximumBytes) {
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
      before.size > maximumBytes
    ) {
      invalid('invalid private input file');
    }

    const bytes = await handle.readFile();
    const after = await handle.stat();

    if (!sameFileState(before, after)) {
      invalid('input file changed while reading');
    }

    const pathState = await lstat(path);

    if (
      pathState.isSymbolicLink() ||
      !pathState.isFile() ||
      !sameFileState(after, pathState)
    ) {
      invalid('input path changed while reading');
    }

    const serialized = new TextDecoder('utf-8', { fatal: true }).decode(bytes);
    return JSON.parse(serialized);
  } catch {
    invalid('invalid private input file');
  } finally {
    await handle?.close().catch(() => {});
  }
}

export function projectApprovedHost(input, generation) {
  if (!isPlainObject(input)) throw new DataFault('shape_invalid');

  const rawExecutorReport = isPlainObject(
    input.selectedExecutorReport,
  )
    ? input.selectedExecutorReport
    : {};

  const spawnRoute = input.spawnRoute === undefined
    ? null
    : {
        accountUuid: projectedText(input.spawnRoute?.accountUuid),
        orgId: projectedText(input.spawnRoute?.orgId),
      };

  const modeEvent =
    input.modeEvent?.generation === generation
      ? {
          mode: projectedText(input.modeEvent.mode),
          at: projectedNumber(input.modeEvent.at),
          generation,
        }
      : null;

  const sessionPermissionUpdateTypes =
    input.sessionPermissionUpdates === undefined
      ? null
      : projectedArray(
          input.sessionPermissionUpdates,
          update => projectedText(update?.type),
        );

  return {
    spawnRoute,
    permissionMode:
      input.permissionMode === undefined
        ? null
        : projectedText(input.permissionMode),
    modeEvent,
    selectedExecutorReport: {
      taskId: retainedText(rawExecutorReport.taskId),
      cliPid: retainedPositiveInteger(rawExecutorReport.cliPid),
      cliPidAtMs:
        retainedTimestamp(rawExecutorReport.cliPidAtMs),
      cliReportedVersion:
        retainedText(rawExecutorReport.cliReportedVersion),
      currentCodeSessionId:
        retainedText(rawExecutorReport.currentCodeSessionId),
      queryGeneration: generation,
      historicProvenance: 'unknown',
      queryToOsAssociation: 'unknown',
      reportBasis:
        'manager-retained-report; not independent OS association',
    },
    harnessCwd:
      input.harnessCwd === undefined
        ? null
        : projectedText(input.harnessCwd, MAX_CWD_BYTES),
    cwdEventProvenance: 'unavailable',
    alwaysAllowedReasons: optionalStringArray(input.alwaysAllowedReasons),
    cuAllowedApps: optionalApps(input.cuAllowedApps),
    cuGrantFlags: optionalFlags(input.cuGrantFlags),
    effectiveCuAllowedApps: optionalApps(input.effectiveCuAllowedApps),
    effectiveCuGrantFlags: optionalFlags(input.effectiveCuGrantFlags),
    sessionPermissionUpdateTypes,
    flagScopeSyncPending:
      input.flagScopeSyncPending === undefined
        ? null
        : projectedBoolean(input.flagScopeSyncPending),
    modeRequestsInFlight:
      input.modeRequestsInFlight === undefined
        ? null
        : projectedCount(input.modeRequestsInFlight),
    pendingCoverage: 'unknown',
  };
}

function validateProjectedHost(value) {
  exactKeys(
    value,
    HOST_KEYS,
    () => {
      throw new DataFault('shape_invalid');
    },
  );

  if (
    value.cwdEventProvenance !== 'unavailable' ||
    value.pendingCoverage !== 'unknown'
  ) {
    throw new DataFault('shape_invalid');
  }

  return value;
}

function projectAccount(value) {
  if (!isPlainObject(value)) throw new DataFault('shape_invalid');

  const cachedProvider =
    value.apiProvider === undefined
      ? null
      : projectedText(value.apiProvider);

  const providerSource =
    value.tokenSource === undefined
      ? null
      : projectedText(value.tokenSource);

  if (cachedProvider === null && providerSource === null) {
    throw new DataFault('shape_invalid');
  }

  return { cachedProvider, providerSource };
}

function projectModel(value) {
  if (!isPlainObject(value)) throw new DataFault('shape_invalid');
  return projectedText(value.model);
}

function projectRules(value) {
  if (!isPlainObject(value) || !isPlainObject(value.state)) {
    throw new DataFault('shape_invalid');
  }

  const state = value.state;

  const rules = projectedArray(state.rules, item => {
    const rule = {
      behavior: projectedText(item?.behavior),
      source: projectedText(item?.source),
      rule: projectedText(item?.rule),
      editability: projectedText(item?.editability),
    };

    if (item?.notInEffect !== undefined) {
      rule.notInEffect = projectedBoolean(item.notInEffect);
    }

    return rule;
  });

  const workspaceGrants = projectedArray(
    state.workspaceDirectories,
    item => ({
      path: projectedText(item?.path, MAX_CWD_BYTES),
      source: projectedText(item?.source),
    }),
  );

  let errorCount = 0;

  if (state.errors !== undefined) {
    if (!Array.isArray(state.errors)) {
      throw new DataFault('shape_invalid');
    }

    if (state.errors.length > MAX_ARRAY_ITEMS) {
      throw new DataFault('limit_exceeded');
    }

    errorCount = state.errors.length;
  }

  return {
    rules,
    workspaceGrants,
    originalCwd: projectedText(state.originalCwd, MAX_CWD_BYTES),
    managedOnly: projectedBoolean(state.managedOnly),
    errorCount,
  };
}

function captureCandidate(config, selectReceiver) {
  const record = selectReceiver(config.targetTaskId);

  if (
    !record ||
    record.taskId !== config.targetTaskId ||
    record.codeSessionId !== config.targetCodeSessionId ||
    !Number.isSafeInteger(record.generation) ||
    record.generation < 1 ||
    !record.query ||
    (typeof record.query !== 'object' &&
      typeof record.query !== 'function') ||
    !record.inputStream
  ) {
    return null;
  }

  return {
    record,
    query: record.query,
    inputStream: record.inputStream,
    generation: record.generation,
    getterRefs: Object.freeze({
      accountInfo: record.query.accountInfo,
      getContextUsage: record.query.getContextUsage,
      listPermissionRules: record.query.listPermissionRules,
    }),
  };
}

const delay = milliseconds =>
  new Promise(resolve => setTimeout(resolve, milliseconds));

async function waitForCandidate(config, selectReceiver, clock) {
  const deadline = clock() + config.setupDeadlineMs;

  while (true) {
    const candidate = captureCandidate(config, selectReceiver);
    if (candidate) return candidate;

    if (clock() >= deadline) invalid('setup deadline exceeded');

    await delay(Math.min(config.pollIntervalMs, Math.max(1, deadline - clock())));
  }
}

function armMatchesBinding(arm, binding) {
  return BINDING_KEYS.every(key => arm[key] === binding[key]);
}

function validateArm(arm, binding) {
  exactKeys(arm, ARM_KEYS);

  if (arm.schema !== ARM_SCHEMA || !armMatchesBinding(arm, binding)) {
    invalid('arm binding mismatch');
  }

  if (
    !Number.isSafeInteger(arm.maxSamples) ||
    arm.maxSamples < 1 ||
    arm.maxSamples > MAX_SAMPLES
  ) {
    invalid('invalid sample limit');
  }

  if (
    !Number.isSafeInteger(arm.minIntervalMs) ||
    arm.minIntervalMs < MIN_SAMPLE_INTERVAL_MS ||
    arm.minIntervalMs > MAX_OBSERVATION_WINDOW_MS
  ) {
    invalid('invalid sample interval');
  }

  if (
    !Number.isSafeInteger(arm.observationWindowMs) ||
    arm.observationWindowMs < 1 ||
    arm.observationWindowMs > MAX_OBSERVATION_WINDOW_MS
  ) {
    invalid('invalid observation window');
  }

  if (
    !Number.isSafeInteger(arm.perGetterTimeoutMs) ||
    arm.perGetterTimeoutMs < 1 ||
    arm.perGetterTimeoutMs > MAX_GETTER_TIMEOUT_MS
  ) {
    invalid('invalid getter timeout');
  }

  return Object.freeze({
    maxSamples: arm.maxSamples,
    minIntervalMs: arm.minIntervalMs,
    observationWindowMs: arm.observationWindowMs,
    perGetterTimeoutMs: arm.perGetterTimeoutMs,
  });
}

function buildBootstrap(binding, config) {
  return {
    schema: BOOTSTRAP_SCHEMA,
    ...binding,
    limits: {
      armDeadlineMs: ARM_DEADLINE_MS,
      maxSamples: MAX_SAMPLES,
      maxObservationWindowMs: MAX_OBSERVATION_WINDOW_MS,
      minSampleIntervalMs: MIN_SAMPLE_INTERVAL_MS,
      maxGetterInvocationsPerSample: 3,
      maxPerGetterTimeoutMs: MAX_GETTER_TIMEOUT_MS,
      maxSampleDeadlineMs: 3 * MAX_GETTER_TIMEOUT_MS,
      maxSampleBytes: MAX_SAMPLE_BYTES,
      maxRunOutputBytes: MAX_RUN_OUTPUT_BYTES,
      maxRules: MAX_ARRAY_ITEMS,
      maxWorkspaceGrants: MAX_ARRAY_ITEMS,
      maxHostGrantRows: MAX_ARRAY_ITEMS,
      maxTextBytes: MAX_TEXT_BYTES,
      maxCwdBytes: MAX_CWD_BYTES,
      setupDeadlineMs: config.setupDeadlineMs,
    },
    securityNotice: [
      'same-UID code can tamper with the adapter, arm, or output',
      'nonces and hashes identify freshness or bytes; they do not authenticate them',
      'all observations are unqualified and partial',
      'rules, grants, and cwd values may be sensitive',
    ],
  };
}

function buildEnvelope({
  sequence,
  observedAt,
  binding,
  result,
  failureClass,
  observation,
}) {
  return {
    schema: SAMPLE_SCHEMA,
    sequence,
    observedAt,
    state: 'unqualified',
    binding: { ...binding },
    result,
    failureClass,
    observation,
  };
}

async function invokeBounded(
  fn,
  receiver,
  args,
  timeoutMs,
  clock,
  checkLifecycle,
) {
  if (typeof fn !== 'function') {
    return { ok: false, failureClass: 'unsupported' };
  }

  const deadline = clock() + timeoutMs;
  let settled = false;
  let timer;

  const invocation = Promise.resolve().then(async () => {
    const beforeFailure = checkLifecycle();

    if (beforeFailure) {
      return { ok: false, failureClass: beforeFailure };
    }

    if (clock() >= deadline) {
      return { ok: false, failureClass: 'timeout' };
    }

    try {
      const value = await fn.apply(receiver, args);

      if (clock() >= deadline) {
        return { ok: false, failureClass: 'timeout' };
      }

      const afterFailure = checkLifecycle();

      if (afterFailure) {
        return { ok: false, failureClass: afterFailure };
      }

      return { ok: true, value };
    } catch {
      if (clock() >= deadline) {
        return { ok: false, failureClass: 'timeout' };
      }

      return { ok: false, failureClass: 'rejected' };
    }
  });

  const outcome = await new Promise(resolve => {
    const finish = value => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(value);
    };

    timer = setTimeout(
      () => finish({ ok: false, failureClass: 'timeout' }),
      timeoutMs,
    );

    invocation.then(
      value => finish(value),
      () => finish({ ok: false, failureClass: 'rejected' }),
    );
  });

  if (!outcome.ok && outcome.failureClass === 'timeout') {
    invocation.then(
      () => {},
      () => {},
    );
  }

  return outcome;
}

export async function attachProbe({
  config: suppliedConfig,
  selectReceiver,
  approvedHostProjection,
  processIdentity: suppliedProcessIdentity,
  now = Date.now,
}) {
  const config = validateConfig(suppliedConfig);
  const processIdentity = validateProcessIdentity(suppliedProcessIdentity);

  if (typeof selectReceiver !== 'function') {
    invalid('invalid receiver selector');
  }

  if (approvedHostProjection !== projectApprovedHost) {
    invalid('unapproved host projection');
  }

  const clock = () => {
    const value = now();

    if (!Number.isSafeInteger(value) || value < 0) {
      invalid('invalid clock');
    }

    return value;
  };

  await assertRunDirectory(config.runDirectory, processIdentity.uid);
  await assertEntries(config.runDirectory, []);

  const candidate = await waitForCandidate(config, selectReceiver, clock);

  await assertRunDirectory(config.runDirectory, processIdentity.uid);
  await assertEntries(config.runDirectory, []);

  const binding = Object.freeze({
    runId: config.runId,
    configSha256: config.configSha256,
    moduleSha256: config.moduleSha256,
    copiedAsarSha256: config.copiedAsarSha256,
    appStartNonce: randomBytes(32).toString('hex'),
    pid: processIdentity.pid,
    processStartTicks: processIdentity.processStartTicks,
    targetTaskId: config.targetTaskId,
    targetCodeSessionId: config.targetCodeSessionId,
    queryGeneration: candidate.generation,
    getterSetId: GETTER_SET_ID,
  });

  const ownedEntries = new Set();
  let outputBytes = 0;
  let terminal = false;
  let armLimits = null;
  let armedAt = null;
  let attempts = 0;
  let lastSampleStartedAt = null;
  let armInFlight = false;
  let sampleInFlight = false;

  const checkBound = () => {
    let record;

    try {
      record = selectReceiver(config.targetTaskId);
    } catch {
      return false;
    }

    return (
      record === candidate.record &&
      record?.taskId === config.targetTaskId &&
      record?.codeSessionId === config.targetCodeSessionId &&
      record?.generation === candidate.generation &&
      record?.query === candidate.query &&
      record?.inputStream === candidate.inputStream &&
      record.query.accountInfo === candidate.getterRefs.accountInfo &&
      record.query.getContextUsage === candidate.getterRefs.getContextUsage &&
      record.query.listPermissionRules ===
        candidate.getterRefs.listPermissionRules
    );
  };

  const sampleLifecycleFailure = () => {
    if (terminal || !armLimits || armedAt === null) {
      return 'limit_exceeded';
    }

    if (clock() - armedAt >= armLimits.observationWindowMs) {
      return 'limit_exceeded';
    }

    return checkBound() ? null : 'identity_changed';
  };

  const publishJson = async (
    name,
    value,
    maximumBytes,
    checkCurrent = null,
  ) => {
    const serialized = `${JSON.stringify(value)}\n`;
    const bytes = Buffer.byteLength(serialized, 'utf8');

    if (
      bytes > maximumBytes ||
      outputBytes + bytes > MAX_RUN_OUTPUT_BYTES
    ) {
      throw new DataFault('limit_exceeded');
    }

    const temporaryName =
      `.${name}.${randomBytes(16).toString('hex')}.tmp`;
    const temporaryPath = join(config.runDirectory, temporaryName);
    const finalPath = join(config.runDirectory, name);
    let handle;
    let finalLinked = false;

    const assertCurrent = () => {
      const failureClass = checkCurrent?.();

      if (failureClass) {
        throw new DataFault(failureClass);
      }
    };

    try {
      assertCurrent();

      handle = await open(temporaryPath, 'wx', 0o600);
      await handle.writeFile(serialized, 'utf8');
      await handle.sync();

      const stats = await handle.stat();

      if (
        !stats.isFile() ||
        stats.uid !== processIdentity.uid ||
        stats.nlink !== 1 ||
        (stats.mode & 0o7777) !== 0o600
      ) {
        throw new DataFault('io_failed');
      }

      await handle.close();
      handle = null;

      assertCurrent();
      await link(temporaryPath, finalPath);
      finalLinked = true;
      assertCurrent();

      await unlink(temporaryPath);
      await syncDirectory(config.runDirectory);

      assertCurrent();

      outputBytes += bytes;
      ownedEntries.add(name);
    } catch (error) {
      await handle?.close().catch(() => {});
      await unlink(temporaryPath).catch(() => {});

      if (finalLinked) {
        await unlink(finalPath).catch(() => {});
        await syncDirectory(config.runDirectory).catch(() => {});
      }

      if (error instanceof DataFault) throw error;
      throw new DataFault('io_failed');
    }
  };

  const bootstrap = buildBootstrap(binding, config);

  try {
    await publishJson('bootstrap.json', bootstrap, MAX_SAMPLE_BYTES);
  } catch {
    invalid('bootstrap export failed');
  }

  const bootstrapAt = clock();

  const failAttempt = async (sequence, observedAt, failureClass) => {
    terminal = true;

    const envelope = buildEnvelope({
      sequence,
      observedAt,
      binding,
      result: 'failed',
      failureClass,
      observation: null,
    });

    try {
      await publishJson(
        `sample-${String(sequence).padStart(6, '0')}.json`,
        envelope,
        MAX_SAMPLE_BYTES,
      );
    } catch {
      invalid('sample export failed');
    }

    return envelope;
  };

  const acceptArm = async () => {
    if (terminal || armLimits || armInFlight) {
      invalid('probe cannot be armed');
    }

    armInFlight = true;

    try {
      const assertArmDeadline = () => {
        if (clock() - bootstrapAt > ARM_DEADLINE_MS) {
          invalid('arm deadline exceeded');
        }
      };

      assertArmDeadline();

      await assertRunDirectory(
        config.runDirectory,
        processIdentity.uid,
      );
      await assertEntries(config.runDirectory, [
        ...ownedEntries,
        'arm.json',
      ]);

      assertArmDeadline();

      const arm = await readPrivateJson(
        join(config.runDirectory, 'arm.json'),
        processIdentity.uid,
        MAX_CONFIG_BYTES,
      );

      assertArmDeadline();

      const acceptedLimits = validateArm(arm, binding);

      if (!checkBound()) {
        invalid('binding changed before arm');
      }

      const acceptedAt = clock();

      if (acceptedAt - bootstrapAt > ARM_DEADLINE_MS) {
        invalid('arm deadline exceeded');
      }

      armLimits = acceptedLimits;
      armedAt = acceptedAt;
      ownedEntries.add('arm.json');

      return { state: 'armed', binding: { ...binding } };
    } catch {
      terminal = true;
      invalid('arm acceptance failed');
    } finally {
      armInFlight = false;
    }
  };

  const sample = async () => {
    if (terminal || !armLimits) invalid('probe is not armed');
    if (sampleInFlight) invalid('sample already in progress');

    sampleInFlight = true;

    try {
      const observedAt = clock();
      const sequence = attempts + 1;

      if (attempts >= armLimits.maxSamples) {
        terminal = true;
        invalid('sample limit exceeded');
      }

      if (
        observedAt - armedAt >= armLimits.observationWindowMs ||
        (lastSampleStartedAt !== null &&
          observedAt - lastSampleStartedAt < armLimits.minIntervalMs)
      ) {
        attempts += 1;
        lastSampleStartedAt = observedAt;
        return await failAttempt(
          sequence,
          observedAt,
          'limit_exceeded',
        );
      }

      attempts += 1;
      lastSampleStartedAt = observedAt;

      try {
        await assertRunDirectory(
          config.runDirectory,
          processIdentity.uid,
        );
        await assertEntries(config.runDirectory, ownedEntries);
      } catch {
        terminal = true;
        invalid('sample input validation failed');
      }

      const fields = {};

      const captureHost = () => {
        const startedAt = clock();
        const beforeFailure = sampleLifecycleFailure();

        if (beforeFailure) {
          return { failureClass: beforeFailure };
        }

        let value;

        try {
          value = validateProjectedHost(
            approvedHostProjection(
              candidate.record.host,
              candidate.generation,
            ),
          );
        } catch (error) {
          return {
            failureClass:
              error instanceof DataFault
                ? error.kind
                : 'shape_invalid',
          };
        }

        const endedAt = clock();
        const afterFailure = sampleLifecycleFailure();

        if (afterFailure) {
          return { failureClass: afterFailure };
        }

        return {
          field: {
            source: 'Desktop manager projection',
            freshness:
              'manager-snapshot; spawn and event values are retained',
            startedAt,
            endedAt,
            value,
          },
        };
      };

      const hostBefore = captureHost();

      if (hostBefore.failureClass) {
        return await failAttempt(
          sequence,
          observedAt,
          hostBefore.failureClass,
        );
      }

      const getters = [
        {
          name: 'accountInfo',
          fieldName: 'accountInfo',
          args: [],
          project: projectAccount,
          source: 'Query.accountInfo',
          freshness: 'initialization-cache',
        },
        {
          name: 'getContextUsage',
          fieldName: 'getContextUsageSummary',
          args: [{ detail: 'summary' }],
          project: projectModel,
          source: 'Query.getContextUsage(summary)',
          freshness: 'query-report; freshness unproven',
        },
        {
          name: 'listPermissionRules',
          fieldName: 'listPermissionRules',
          args: [],
          project: projectRules,
          source: 'Query.listPermissionRules',
          freshness: 'query-report; permission coverage partial',
        },
      ];

      for (const getter of getters) {
        const beforeFailure = sampleLifecycleFailure();

        if (beforeFailure) {
          return await failAttempt(
            sequence,
            observedAt,
            beforeFailure,
          );
        }

        const startedAt = clock();

        const outcome = await invokeBounded(
          candidate.getterRefs[getter.name],
          candidate.query,
          getter.args,
          armLimits.perGetterTimeoutMs,
          clock,
          sampleLifecycleFailure,
        );

        if (!outcome.ok) {
          return await failAttempt(
            sequence,
            observedAt,
            outcome.failureClass,
          );
        }

        const afterFailure = sampleLifecycleFailure();

        if (afterFailure) {
          return await failAttempt(
            sequence,
            observedAt,
            afterFailure,
          );
        }

        try {
          const value = getter.project(outcome.value);
          const endedAt = clock();

          fields[getter.fieldName] = {
            source: getter.source,
            freshness: getter.freshness,
            startedAt,
            endedAt,
            value,
          };
        } catch (error) {
          return await failAttempt(
            sequence,
            observedAt,
            error instanceof DataFault
              ? error.kind
              : 'shape_invalid',
          );
        }
      }

      const hostAfter = captureHost();

      if (hostAfter.failureClass) {
        return await failAttempt(
          sequence,
          observedAt,
          hostAfter.failureClass,
        );
      }

      fields.hostBefore = hostBefore.field;
      fields.hostAfter = hostAfter.field;
      const collectionEndedAt = clock();

      const beforePublicationFailure = sampleLifecycleFailure();

      if (beforePublicationFailure) {
        return await failAttempt(
          sequence,
          observedAt,
          beforePublicationFailure,
        );
      }

      const observation = {
        collection: {
          startedAt: observedAt,
          endedAt: collectionEndedAt,
          hostChangedDuringRead:
            JSON.stringify(canonicalize(hostBefore.field.value)) !==
            JSON.stringify(canonicalize(hostAfter.field.value)),
        },
        fields,
        unknowns: [...UNKNOWN_CLAIMS],
      };

      let envelope = buildEnvelope({
        sequence,
        observedAt,
        binding,
        result: 'complete',
        failureClass: null,
        observation,
      });

      try {
        await publishJson(
          `sample-${String(sequence).padStart(6, '0')}.json`,
          envelope,
          MAX_SAMPLE_BYTES,
          sampleLifecycleFailure,
        );
      } catch (error) {
        if (
          error instanceof DataFault &&
          (
            error.kind === 'limit_exceeded' ||
            error.kind === 'identity_changed'
          )
        ) {
          envelope = await failAttempt(
            sequence,
            observedAt,
            error.kind,
          );
        } else {
          terminal = true;
          invalid('sample export failed');
        }
      }

      if (attempts >= armLimits.maxSamples) terminal = true;

      return envelope;
    } finally {
      sampleInFlight = false;
    }
  };

  return {
    bootstrap,
    acceptArm,
    sample,
    get state() {
      if (terminal) return 'terminal';
      if (armLimits) return 'armed';
      return 'disarmed';
    },
  };
}
