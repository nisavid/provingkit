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
import {
  ARM_DEADLINE_MS,
  ARM_KEYS,
  BINDING_KEYS,
  ARM_SCHEMA,
  BOOTSTRAP_SCHEMA,
  CONFIG_SCHEMA,
  FAILURE_CLASSES,
  GETTER_SET_ID,
  HOST_GAP_FIELDS,
  HOST_KEYS,
  MAX_ARRAY_ITEMS,
  MAX_CONFIG_BYTES,
  MAX_CWD_BYTES,
  MAX_GETTER_TIMEOUT_MS,
  MAX_OBSERVATION_WINDOW_MS,
  MAX_RUN_OUTPUT_BYTES,
  MAX_SAMPLE_BYTES,
  MAX_SAMPLES,
  MAX_SETUP_DEADLINE_MS,
  MAX_TEXT_BYTES,
  MIN_SAMPLE_INTERVAL_MS,
  MONOTONIC_CLOCK_ID,
  SAMPLE_SCHEMA,
  isValidLinuxBootId,
  SELECTED_EXECUTOR_REPORT_BASIS,
  SELECTED_EXECUTOR_REPORT_KEYS,
  UNKNOWN_CLAIMS,
} from './observer-contract.mjs';

export {
  ARM_SCHEMA,
  BOOTSTRAP_SCHEMA,
  CONFIG_SCHEMA,
  GETTER_SET_ID,
  SAMPLE_SCHEMA,
} from './observer-contract.mjs';

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
  exactKeys(input, [
    'pid',
    'processStartTicks',
    'uid',
    'monotonicClockId',
    'linuxBootId',
  ]);

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

  if (
    input.monotonicClockId !== MONOTONIC_CLOCK_ID ||
    !isValidLinuxBootId(input.linuxBootId)
  ) {
    invalid('invalid monotonic clock domain');
  }

  return Object.freeze({
    pid: input.pid,
    processStartTicks: input.processStartTicks,
    uid: input.uid,
    monotonicClockId: input.monotonicClockId,
    linuxBootId: input.linuxBootId,
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

  const failures = isPlainObject(input.fieldFailures)
    ? input.fieldFailures
    : {};
  const gaps = [];
  const gapFields = new Set(HOST_GAP_FIELDS);
  const failureClasses = new Set(FAILURE_CLASSES);

  const addGap = (field, failureClass) => {
    if (
      !gapFields.has(field) ||
      !failureClasses.has(failureClass) ||
      gaps.some(gap => gap.field === field)
    ) {
      return;
    }

    gaps.push({ field, failureClass });
  };

  const project = (
    field,
    value,
    projector,
    fallback = null,
  ) => {
    const suppliedFailure = failures[field];

    if (failureClasses.has(suppliedFailure)) {
      addGap(field, suppliedFailure);
      return fallback;
    }

    if (value === undefined || value === null) {
      addGap(field, 'unavailable');
      return fallback;
    }

    try {
      return projector(value);
    } catch (error) {
      addGap(
        field,
        error instanceof DataFault ? error.kind : 'shape_invalid',
      );
      return fallback;
    }
  };

  const spawnRoute = project(
    'spawnRoute',
    input.spawnRoute,
    value => ({
      accountUuid: projectedText(value?.accountUuid),
      orgId: projectedText(value?.orgId),
    }),
  );

  const modeEvent = project(
    'modeEvent',
    input.modeEvent,
    value => {
      if (value?.generation !== generation) {
        throw new DataFault('shape_invalid');
      }

      return {
        mode: projectedText(value.mode),
        at: projectedNumber(value.at),
        generation,
      };
    },
  );

  let rawExecutorReport = input.selectedExecutorReport;

  if (!isPlainObject(rawExecutorReport)) {
    addGap(
      'selectedExecutorReport',
      rawExecutorReport === undefined || rawExecutorReport === null
        ? 'unavailable'
        : 'shape_invalid',
    );
    rawExecutorReport = {};
  }

  const reportText = field =>
    project(
      `selectedExecutorReport.${field}`,
      rawExecutorReport[field],
      value => projectedText(value),
    );

  const reportInteger = (field, allowZero) =>
    project(
      `selectedExecutorReport.${field}`,
      rawExecutorReport[field],
      value => {
        if (
          !Number.isSafeInteger(value) ||
          value < (allowZero ? 0 : 1)
        ) {
          throw new DataFault('shape_invalid');
        }

        return value;
      },
    );

  return {
    spawnRoute,
    permissionMode: project(
      'permissionMode',
      input.permissionMode,
      value => projectedText(value),
    ),
    modeEvent,
    selectedExecutorReport: {
      taskId: reportText('taskId'),
      cliPid: reportInteger('cliPid', false),
      cliPidAtMs: reportInteger('cliPidAtMs', true),
      cliReportedVersion: reportText('cliReportedVersion'),
      currentCodeSessionId: reportText('currentCodeSessionId'),
      queryGeneration: generation,
      historicProvenance: 'unknown',
      queryToOsAssociation: 'unknown',
      reportBasis: SELECTED_EXECUTOR_REPORT_BASIS,
    },
    harnessCwd: project(
      'harnessCwd',
      input.harnessCwd,
      value => projectedText(value, MAX_CWD_BYTES),
    ),
    cwdEventProvenance: 'unavailable',
    alwaysAllowedReasons: project(
      'alwaysAllowedReasons',
      input.alwaysAllowedReasons,
      optionalStringArray,
    ),
    cuAllowedApps: project(
      'cuAllowedApps',
      input.cuAllowedApps,
      optionalApps,
    ),
    cuGrantFlags: project(
      'cuGrantFlags',
      input.cuGrantFlags,
      optionalFlags,
    ),
    effectiveCuAllowedApps: project(
      'effectiveCuAllowedApps',
      input.effectiveCuAllowedApps,
      optionalApps,
    ),
    effectiveCuGrantFlags: project(
      'effectiveCuGrantFlags',
      input.effectiveCuGrantFlags,
      optionalFlags,
    ),
    sessionPermissionUpdateTypes: project(
      'sessionPermissionUpdateTypes',
      input.sessionPermissionUpdates,
      value => projectedArray(
        value,
        update => projectedText(update?.type),
      ),
    ),
    flagScopeSyncPending: project(
      'flagScopeSyncPending',
      input.flagScopeSyncPending,
      projectedBoolean,
    ),
    modeRequestsInFlight: project(
      'modeRequestsInFlight',
      input.modeRequestsInFlight,
      projectedCount,
    ),
    pendingCoverage: 'unknown',
    gaps,
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

  exactKeys(
    value.selectedExecutorReport,
    SELECTED_EXECUTOR_REPORT_KEYS,
    () => {
      throw new DataFault('shape_invalid');
    },
  );

  if (
    !Array.isArray(value.gaps) ||
    value.gaps.length > HOST_GAP_FIELDS.length
  ) {
    throw new DataFault('shape_invalid');
  }

  const seen = new Set();

  for (const gap of value.gaps) {
    exactKeys(gap, ['field', 'failureClass'], () => {
      throw new DataFault('shape_invalid');
    });

    if (
      !HOST_GAP_FIELDS.includes(gap.field) ||
      !FAILURE_CLASSES.includes(gap.failureClass) ||
      seen.has(gap.field)
    ) {
      throw new DataFault('shape_invalid');
    }

    seen.add(gap.field);
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

  if (!Array.isArray(state.errors)) {
    throw new DataFault('shape_invalid');
  }

  if (state.errors.length > MAX_ARRAY_ITEMS) {
    throw new DataFault('limit_exceeded');
  }

  return {
    rules,
    workspaceGrants,
    originalCwd: projectedText(state.originalCwd, MAX_CWD_BYTES),
    managedOnly: projectedBoolean(state.managedOnly),
    errorCount: state.errors.length,
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

async function waitForCandidate(config, selectReceiver, elapsedClock) {
  const deadline = elapsedClock() + config.setupDeadlineMs;

  while (true) {
    if (elapsedClock() >= deadline) {
      invalid('setup deadline exceeded');
    }

    const candidate = captureCandidate(config, selectReceiver);

    if (candidate) {
      if (elapsedClock() >= deadline) {
        invalid('setup deadline exceeded');
      }

      return candidate;
    }

    await delay(Math.min(
      config.pollIntervalMs,
      Math.max(1, deadline - elapsedClock()),
    ));
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
  observedAtMonotonicMs,
  binding,
  result,
  failureClass,
  failureStage,
  observation,
}) {
  return {
    schema: SAMPLE_SCHEMA,
    sequence,
    observedAt,
    observedAtMonotonicMs,
    state: 'unqualified',
    binding: { ...binding },
    result,
    failureClass,
    failureStage,
    observation,
  };
}

async function invokeBounded(
  fn,
  receiver,
  args,
  deadline,
  elapsedClock,
  checkLifecycle,
) {
  const deadlineFailure = () => {
    const lifecycleFailure = checkLifecycle();

    if (lifecycleFailure) return lifecycleFailure;
    return elapsedClock() >= deadline ? 'timeout' : null;
  };

  const initialFailure = deadlineFailure();

  if (initialFailure) {
    return { ok: false, failureClass: initialFailure };
  }

  if (typeof fn !== 'function') {
    return { ok: false, failureClass: 'unsupported' };
  }

  let settled = false;
  let timer;

  const invocation = Promise.resolve().then(async () => {
    const beforeFailure = deadlineFailure();

    if (beforeFailure) {
      return { ok: false, failureClass: beforeFailure };
    }

    try {
      const value = await fn.apply(receiver, args);
      const afterFailure = deadlineFailure();

      if (afterFailure) {
        return { ok: false, failureClass: afterFailure };
      }

      return { ok: true, value };
    } catch {
      const afterFailure = deadlineFailure();

      if (afterFailure) {
        return { ok: false, failureClass: afterFailure };
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

    const remainingMs = Math.max(0, deadline - elapsedClock());

    timer = setTimeout(
      () => {
        let failureClass = 'timeout';

        try {
          failureClass = deadlineFailure() ?? 'timeout';
        } catch {}

        finish({ ok: false, failureClass });
      },
      remainingMs,
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
  monotonicNow = () =>
    Number(process.hrtime.bigint() / 1_000_000n),
}) {
  const config = validateConfig(suppliedConfig);
  const processIdentity = validateProcessIdentity(suppliedProcessIdentity);

  if (typeof selectReceiver !== 'function') {
    invalid('invalid receiver selector');
  }

  if (approvedHostProjection !== projectApprovedHost) {
    invalid('unapproved host projection');
  }

  const wallClock = () => {
    const value = now();

    if (!Number.isSafeInteger(value) || value < 0) {
      invalid('invalid wall clock');
    }

    return value;
  };

  const elapsedClock = () => {
    const value = monotonicNow();

    if (!Number.isSafeInteger(value) || value < 0) {
      invalid('invalid monotonic clock');
    }

    return value;
  };

  await assertRunDirectory(config.runDirectory, processIdentity.uid);
  await assertEntries(config.runDirectory, []);

  const candidate = await waitForCandidate(
    config,
    selectReceiver,
    elapsedClock,
  );

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
    monotonicClockId: processIdentity.monotonicClockId,
    linuxBootId: processIdentity.linuxBootId,
  });

  const ownedEntries = new Set();
  let outputBytes = 0;
  let terminal = false;
  let armLimits = null;
  let observationDeadlineElapsed = null;
  let attempts = 0;
  let lastSampleStartedAtElapsed = null;
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
    if (
      terminal ||
      !armLimits ||
      observationDeadlineElapsed === null
    ) {
      return 'limit_exceeded';
    }

    if (elapsedClock() >= observationDeadlineElapsed) {
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

  const bootstrapAtElapsed = elapsedClock();

  const failAttempt = async (
    sequence,
    observedAt,
    observedAtMonotonicMs,
    failureClass,
    failureStage,
  ) => {
    terminal = true;

    const envelope = buildEnvelope({
      sequence,
      observedAt,
      observedAtMonotonicMs,
      binding,
      result: 'failed',
      failureClass,
      failureStage,
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
        if (
          elapsedClock() - bootstrapAtElapsed >
          ARM_DEADLINE_MS
        ) {
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

      const acceptedAtElapsed = elapsedClock();

      if (
        acceptedAtElapsed - bootstrapAtElapsed >
        ARM_DEADLINE_MS
      ) {
        invalid('arm deadline exceeded');
      }

      if (
        acceptedAtElapsed >
        Number.MAX_SAFE_INTEGER -
          acceptedLimits.observationWindowMs
      ) {
        invalid('invalid monotonic clock');
      }

      armLimits = acceptedLimits;
      observationDeadlineElapsed =
        acceptedAtElapsed +
        acceptedLimits.observationWindowMs;
      ownedEntries.add('arm.json');

      return {
        state: 'armed',
        binding: { ...binding },
        limits: { ...armLimits },
      };
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
      const sampleStartedAtElapsed = elapsedClock();
      const observedAtMonotonicMs = sampleStartedAtElapsed;
      const observedAt = wallClock();
      const sequence = attempts + 1;

      if (attempts >= armLimits.maxSamples) {
        terminal = true;
        invalid('sample limit exceeded');
      }

      if (
        sampleStartedAtElapsed >= observationDeadlineElapsed ||
        (
          lastSampleStartedAtElapsed !== null &&
          sampleStartedAtElapsed - lastSampleStartedAtElapsed <
            armLimits.minIntervalMs
        )
      ) {
        attempts += 1;
        lastSampleStartedAtElapsed = sampleStartedAtElapsed;
        return await failAttempt(
          sequence,
          observedAt,
          observedAtMonotonicMs,
          'limit_exceeded',
          'lifecycle',
        );
      }

      attempts += 1;
      lastSampleStartedAtElapsed = sampleStartedAtElapsed;

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

      const availableField = (
        source,
        freshness,
        startedAt,
        endedAt,
        value,
      ) => ({
        source,
        freshness,
        startedAt,
        endedAt,
        status: 'available',
        failureClass: null,
        failureStage: null,
        value,
      });

      const unavailableField = (
        source,
        freshness,
        startedAt,
        endedAt,
        failureClass,
        failureStage,
      ) => ({
        source,
        freshness,
        startedAt,
        endedAt,
        status: 'unavailable',
        failureClass,
        failureStage,
        value: null,
      });

      const validWallInterval = (startedAt, endedAt) =>
        startedAt >= observedAt &&
        endedAt >= startedAt &&
        endedAt - observedAt <= MAX_OBSERVATION_WINDOW_MS;

      const captureHost = stage => {
        const source = 'Desktop manager projection';
        const freshness =
          'manager-snapshot; spawn and event values are retained';
        const startedAt = wallClock();

        try {
          const value = validateProjectedHost(
            approvedHostProjection(
              candidate.record.host,
              candidate.generation,
            ),
          );
          const endedAt = wallClock();

          if (!validWallInterval(startedAt, endedAt)) {
            return { wallInvalid: true };
          }

          return {
            field: availableField(
              source,
              freshness,
              startedAt,
              endedAt,
              value,
            ),
          };
        } catch (error) {
          const endedAt = wallClock();

          if (!validWallInterval(startedAt, endedAt)) {
            return { wallInvalid: true };
          }

          return {
            field: unavailableField(
              source,
              freshness,
              startedAt,
              endedAt,
              error instanceof DataFault
                ? error.kind
                : 'shape_invalid',
              stage,
            ),
          };
        };
      };

      let lifecycleFailure = sampleLifecycleFailure();

      if (lifecycleFailure) {
        return await failAttempt(
          sequence,
          observedAt,
          observedAtMonotonicMs,
          lifecycleFailure,
          'hostBefore',
        );
      }

      const hostBefore = captureHost('hostBefore');

      if (hostBefore.wallInvalid) {
        return await failAttempt(
          sequence,
          observedAt,
          observedAtMonotonicMs,
          'shape_invalid',
          'wallClock',
        );
      }

      lifecycleFailure = sampleLifecycleFailure();

      if (lifecycleFailure) {
        return await failAttempt(
          sequence,
          observedAt,
          observedAtMonotonicMs,
          lifecycleFailure,
          'hostBefore',
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
            observedAtMonotonicMs,
            beforeFailure,
            getter.fieldName,
          );
        }

        const getterStartedAtElapsed = elapsedClock();
        const remainingObservationMs =
          observationDeadlineElapsed - getterStartedAtElapsed;

        if (remainingObservationMs <= 0) {
          return await failAttempt(
            sequence,
            observedAt,
            observedAtMonotonicMs,
            'limit_exceeded',
            getter.fieldName,
          );
        }

        const startedAt = wallClock();
        const getterDeadlineElapsed =
          getterStartedAtElapsed +
          Math.min(
            armLimits.perGetterTimeoutMs,
            remainingObservationMs,
          );

        const outcome = await invokeBounded(
          candidate.getterRefs[getter.name],
          candidate.query,
          getter.args,
          getterDeadlineElapsed,
          elapsedClock,
          sampleLifecycleFailure,
        );

        if (!outcome.ok) {
          const endedAt = wallClock();

          if (!validWallInterval(startedAt, endedAt)) {
            return await failAttempt(
              sequence,
              observedAt,
              observedAtMonotonicMs,
              'shape_invalid',
              'wallClock',
            );
          }

          if (
            outcome.failureClass === 'timeout' ||
            outcome.failureClass === 'identity_changed' ||
            outcome.failureClass === 'limit_exceeded'
          ) {
            return await failAttempt(
              sequence,
              observedAt,
              observedAtMonotonicMs,
              outcome.failureClass,
              getter.fieldName,
            );
          }

          fields[getter.fieldName] = unavailableField(
            getter.source,
            getter.freshness,
            startedAt,
            endedAt,
            outcome.failureClass,
            getter.fieldName,
          );
          continue;
        }

        const afterFailure = sampleLifecycleFailure();

        if (afterFailure) {
          return await failAttempt(
            sequence,
            observedAt,
            observedAtMonotonicMs,
            afterFailure,
            getter.fieldName,
          );
        }

        try {
          const value = getter.project(outcome.value);
          const endedAt = wallClock();

          if (!validWallInterval(startedAt, endedAt)) {
            return await failAttempt(
              sequence,
              observedAt,
              observedAtMonotonicMs,
              'shape_invalid',
              'wallClock',
            );
          }

          fields[getter.fieldName] = availableField(
            getter.source,
            getter.freshness,
            startedAt,
            endedAt,
            value,
          );
        } catch (error) {
          const endedAt = wallClock();

          if (!validWallInterval(startedAt, endedAt)) {
            return await failAttempt(
              sequence,
              observedAt,
              observedAtMonotonicMs,
              'shape_invalid',
              'wallClock',
            );
          }

          fields[getter.fieldName] = unavailableField(
            getter.source,
            getter.freshness,
            startedAt,
            endedAt,
            error instanceof DataFault
              ? error.kind
              : 'shape_invalid',
            getter.fieldName,
          );
        }
      }

      lifecycleFailure = sampleLifecycleFailure();

      if (lifecycleFailure) {
        return await failAttempt(
          sequence,
          observedAt,
          observedAtMonotonicMs,
          lifecycleFailure,
          'hostAfter',
        );
      }

      const hostAfter = captureHost('hostAfter');

      if (hostAfter.wallInvalid) {
        return await failAttempt(
          sequence,
          observedAt,
          observedAtMonotonicMs,
          'shape_invalid',
          'wallClock',
        );
      }

      lifecycleFailure = sampleLifecycleFailure();

      if (lifecycleFailure) {
        return await failAttempt(
          sequence,
          observedAt,
          observedAtMonotonicMs,
          lifecycleFailure,
          'hostAfter',
        );
      }

      fields.hostBefore = hostBefore.field;
      fields.hostAfter = hostAfter.field;
      const collectionEndedAt = wallClock();
      const collectionEndedAtMonotonicMs = elapsedClock();

      if (
        !validWallInterval(observedAt, collectionEndedAt) ||
        collectionEndedAtMonotonicMs < observedAtMonotonicMs ||
        collectionEndedAtMonotonicMs - observedAtMonotonicMs >
          MAX_OBSERVATION_WINDOW_MS
      ) {
        return await failAttempt(
          sequence,
          observedAt,
          observedAtMonotonicMs,
          'shape_invalid',
          'wallClock',
        );
      }

      const beforePublicationFailure = sampleLifecycleFailure();

      if (beforePublicationFailure) {
        return await failAttempt(
          sequence,
          observedAt,
          observedAtMonotonicMs,
          beforePublicationFailure,
          'publication',
        );
      }

      const hostsComparable =
        hostBefore.field.status === 'available' &&
        hostAfter.field.status === 'available';

      const observation = {
        collection: {
          startedAt: observedAt,
          endedAt: collectionEndedAt,
          startedAtMonotonicMs: observedAtMonotonicMs,
          endedAtMonotonicMs: collectionEndedAtMonotonicMs,
          hostChangedDuringRead:
            hostsComparable
              ? JSON.stringify(
                  canonicalize(hostBefore.field.value),
                ) !== JSON.stringify(
                  canonicalize(hostAfter.field.value),
                )
              : null,
        },
        fields,
        unknowns: [...UNKNOWN_CLAIMS],
      };

      const isPartial = Object.values(fields).some(field =>
        field.status === 'unavailable' ||
        (
          field.status === 'available' &&
          Array.isArray(field.value?.gaps) &&
          field.value.gaps.length > 0
        ),
      );

      let envelope = buildEnvelope({
        sequence,
        observedAt,
        observedAtMonotonicMs,
        binding,
        result: isPartial ? 'partial' : 'complete',
        failureClass: null,
        failureStage: null,
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
            observedAtMonotonicMs,
            error.kind,
            'publication',
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
