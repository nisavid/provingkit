const SAMPLE_SCHEMA = 'desktop-observer.sample.v1';
const GETTER_SET_ID =
  'desktop-query.readonly.v1:accountInfo,getContextUsage-summary,listPermissionRules';

const MAX_SAMPLE_BYTES = 16 * 1024;
const MAX_OBSERVATION_WINDOW_MS = 30_000;
const MAX_ARRAY_ITEMS = 32;
const MAX_TEXT_BYTES = 256;
const MAX_CWD_BYTES = 1024;
const MAX_PARSE_DEPTH = 32;

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

const FAILURE_CLASSES = new Set([
  'unsupported',
  'limit_exceeded',
  'timeout',
  'identity_changed',
  'rejected',
  'shape_invalid',
]);

const invalid = () => {
  throw new Error('invalid sample');
};

const isPlainObject = value => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return false;
  }

  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
};

function exactKeys(value, expected) {
  if (!isPlainObject(value)) invalid();

  const actual = Object.keys(value).sort();
  const sortedExpected = [...expected].sort();

  if (
    actual.length !== sortedExpected.length ||
    actual.some((key, index) => key !== sortedExpected[index])
  ) {
    invalid();
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

const canonical = value => JSON.stringify(canonicalize(value));

const hasControlCharacters = value =>
  /[\u0000-\u001f\u007f]/u.test(value);

function text(value, maximum = MAX_TEXT_BYTES) {
  if (
    typeof value !== 'string' ||
    value.length === 0 ||
    hasControlCharacters(value) ||
    Buffer.byteLength(value, 'utf8') > maximum
  ) {
    invalid();
  }

  return value;
}

function nullableText(value, maximum = MAX_TEXT_BYTES) {
  if (value === null) return null;
  return text(value, maximum);
}

function timestamp(value) {
  if (!Number.isSafeInteger(value) || value < 0) invalid();
  return value;
}

function count(value) {
  if (!Number.isSafeInteger(value) || value < 0) invalid();
  return value;
}

function nonnegativeNumber(value) {
  if (!Number.isFinite(value) || value < 0) invalid();
  return value;
}

function boolean(value) {
  if (typeof value !== 'boolean') invalid();
  return value;
}

function boundedArray(value, validateItem) {
  if (!Array.isArray(value) || value.length > MAX_ARRAY_ITEMS) {
    invalid();
  }

  value.forEach(validateItem);
  return value;
}

function parseStrictJson(serialized) {
  let index = 0;

  const skipWhitespace = () => {
    while (
      serialized[index] === ' ' ||
      serialized[index] === '\n' ||
      serialized[index] === '\r' ||
      serialized[index] === '\t'
    ) {
      index += 1;
    }
  };

  const parseString = () => {
    const start = index;
    index += 1;

    while (index < serialized.length) {
      const code = serialized.charCodeAt(index);
      const character = serialized[index];
      index += 1;

      if (character === '"') {
        return JSON.parse(serialized.slice(start, index));
      }

      if (code < 0x20) invalid();

      if (character === '\\') {
        const escaped = serialized[index];

        if (escaped === 'u') {
          if (
            !/^[0-9a-fA-F]{4}$/u.test(
              serialized.slice(index + 1, index + 5),
            )
          ) {
            invalid();
          }

          index += 5;
        } else if ('"\\/bfnrt'.includes(escaped)) {
          index += 1;
        } else {
          invalid();
        }
      }
    }

    invalid();
  };

  const parseNumber = () => {
    const pattern =
      /-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/y;
    pattern.lastIndex = index;
    const match = pattern.exec(serialized);

    if (!match) invalid();

    index = pattern.lastIndex;
    return Number(match[0]);
  };

  const parseValue = depth => {
    if (depth > MAX_PARSE_DEPTH) invalid();

    skipWhitespace();
    const character = serialized[index];

    if (character === '"') return parseString();
    if (character === '-' || /[0-9]/u.test(character ?? '')) {
      return parseNumber();
    }

    if (serialized.startsWith('true', index)) {
      index += 4;
      return true;
    }

    if (serialized.startsWith('false', index)) {
      index += 5;
      return false;
    }

    if (serialized.startsWith('null', index)) {
      index += 4;
      return null;
    }

    if (character === '[') {
      index += 1;
      skipWhitespace();
      const result = [];

      if (serialized[index] === ']') {
        index += 1;
        return result;
      }

      while (true) {
        result.push(parseValue(depth + 1));
        skipWhitespace();

        if (serialized[index] === ']') {
          index += 1;
          return result;
        }

        if (serialized[index] !== ',') invalid();
        index += 1;
      }
    }

    if (character === '{') {
      index += 1;
      skipWhitespace();
      const result = {};
      const keys = new Set();

      if (serialized[index] === '}') {
        index += 1;
        return result;
      }

      while (true) {
        skipWhitespace();
        if (serialized[index] !== '"') invalid();

        const key = parseString();
        if (keys.has(key)) invalid();
        keys.add(key);

        skipWhitespace();
        if (serialized[index] !== ':') invalid();
        index += 1;

        Object.defineProperty(result, key, {
          value: parseValue(depth + 1),
          enumerable: true,
          configurable: true,
          writable: true,
        });

        skipWhitespace();

        if (serialized[index] === '}') {
          index += 1;
          return result;
        }

        if (serialized[index] !== ',') invalid();
        index += 1;
      }
    }

    invalid();
  };

  const value = parseValue(0);
  skipWhitespace();

  if (index !== serialized.length) invalid();
  return value;
}

function validateBinding(binding) {
  exactKeys(binding, BINDING_KEYS);

  for (const key of [
    'runId',
    'targetTaskId',
    'targetCodeSessionId',
  ]) {
    text(binding[key]);
  }

  for (const key of [
    'configSha256',
    'moduleSha256',
    'copiedAsarSha256',
    'appStartNonce',
  ]) {
    if (!/^[a-f0-9]{64}$/u.test(binding[key])) invalid();
  }

  if (!Number.isSafeInteger(binding.pid) || binding.pid < 1) invalid();

  if (
    typeof binding.processStartTicks !== 'string' ||
    !/^[0-9]+$/u.test(binding.processStartTicks)
  ) {
    invalid();
  }

  if (
    !Number.isSafeInteger(binding.queryGeneration) ||
    binding.queryGeneration < 1
  ) {
    invalid();
  }

  if (binding.getterSetId !== GETTER_SET_ID) invalid();
  return binding;
}

function validateFlags(value) {
  if (value === null) return;
  if (!isPlainObject(value)) invalid();

  const approved = new Set([
    'clipboardRead',
    'clipboardWrite',
    'systemKeyCombos',
  ]);

  if (Object.keys(value).some(key => !approved.has(key))) invalid();
  Object.values(value).forEach(boolean);
}

function validateApps(value) {
  if (value === null) return;

  boundedArray(value, item => {
    exactKeys(item, ['bundleId', 'grantedAt']);
    text(item.bundleId);
    nonnegativeNumber(item.grantedAt);
  });
}

function validateSelectedExecutorReport(value, binding) {
  exactKeys(value, [
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

  nullableText(value.taskId);

  if (
    value.cliPid !== null &&
    (
      !Number.isSafeInteger(value.cliPid) ||
      value.cliPid < 1
    )
  ) {
    invalid();
  }

  if (value.cliPidAtMs !== null) {
    timestamp(value.cliPidAtMs);
  }

  nullableText(value.cliReportedVersion);
  nullableText(value.currentCodeSessionId);

  if (
    value.queryGeneration !== binding.queryGeneration ||
    (
      value.taskId !== null &&
      value.taskId !== binding.targetTaskId
    ) ||
    (
      value.currentCodeSessionId !== null &&
      value.currentCodeSessionId !==
        binding.targetCodeSessionId
    ) ||
    value.historicProvenance !== 'unknown' ||
    value.queryToOsAssociation !== 'unknown' ||
    value.reportBasis !==
      'manager-retained-report; not independent OS association'
  ) {
    invalid();
  }
}

function validateHost(value, binding) {
  exactKeys(value, HOST_KEYS);

  if (value.spawnRoute !== null) {
    exactKeys(value.spawnRoute, ['accountUuid', 'orgId']);
    text(value.spawnRoute.accountUuid);
    text(value.spawnRoute.orgId);
  }

  nullableText(value.permissionMode);

  if (value.modeEvent !== null) {
    exactKeys(value.modeEvent, ['mode', 'at', 'generation']);
    text(value.modeEvent.mode);
    nonnegativeNumber(value.modeEvent.at);
    if (
      value.modeEvent.generation !== binding.queryGeneration
    ) {
      invalid();
    }
  }

  validateSelectedExecutorReport(
    value.selectedExecutorReport,
    binding,
  );

  nullableText(value.harnessCwd, MAX_CWD_BYTES);

  if (
    value.cwdEventProvenance !== 'unavailable' ||
    value.pendingCoverage !== 'unknown'
  ) {
    invalid();
  }

  if (value.alwaysAllowedReasons !== null) {
    boundedArray(value.alwaysAllowedReasons, item => text(item));
  }

  validateApps(value.cuAllowedApps);
  validateFlags(value.cuGrantFlags);
  validateApps(value.effectiveCuAllowedApps);
  validateFlags(value.effectiveCuGrantFlags);

  if (value.sessionPermissionUpdateTypes !== null) {
    boundedArray(
      value.sessionPermissionUpdateTypes,
      item => text(item),
    );
  }

  if (value.flagScopeSyncPending !== null) {
    boolean(value.flagScopeSyncPending);
  }

  if (value.modeRequestsInFlight !== null) {
    count(value.modeRequestsInFlight);
  }
}

function validateAccount(value) {
  exactKeys(value, ['cachedProvider', 'providerSource']);
  nullableText(value.cachedProvider);
  nullableText(value.providerSource);

  if (
    value.cachedProvider === null &&
    value.providerSource === null
  ) {
    invalid();
  }
}

function validateRules(value) {
  exactKeys(value, [
    'rules',
    'workspaceGrants',
    'originalCwd',
    'managedOnly',
    'errorCount',
  ]);

  boundedArray(value.rules, rule => {
    const keys = [
      'behavior',
      'source',
      'rule',
      'editability',
      ...(
        Object.prototype.hasOwnProperty.call(rule, 'notInEffect')
          ? ['notInEffect']
          : []
      ),
    ];

    exactKeys(rule, keys);
    text(rule.behavior);
    text(rule.source);
    text(rule.rule);
    text(rule.editability);

    if ('notInEffect' in rule) boolean(rule.notInEffect);
  });

  boundedArray(value.workspaceGrants, grant => {
    exactKeys(grant, ['path', 'source']);
    text(grant.path, MAX_CWD_BYTES);
    text(grant.source);
  });

  text(value.originalCwd, MAX_CWD_BYTES);
  boolean(value.managedOnly);
  count(value.errorCount);

  if (value.errorCount > MAX_ARRAY_ITEMS) invalid();
}

function validateField(
  field,
  collection,
  { source, freshness, validateValue },
) {
  exactKeys(field, [
    'source',
    'freshness',
    'startedAt',
    'endedAt',
    'value',
  ]);

  if (field.source !== source || field.freshness !== freshness) {
    invalid();
  }

  timestamp(field.startedAt);
  timestamp(field.endedAt);

  if (
    field.startedAt < collection.startedAt ||
    field.endedAt < field.startedAt ||
    field.endedAt > collection.endedAt
  ) {
    invalid();
  }

  validateValue(field.value);
}

function validateObservation(observation, binding, observedAt) {
  exactKeys(observation, ['collection', 'fields', 'unknowns']);

  const collection = observation.collection;
  exactKeys(collection, [
    'startedAt',
    'endedAt',
    'hostChangedDuringRead',
  ]);

  timestamp(collection.startedAt);
  timestamp(collection.endedAt);
  boolean(collection.hostChangedDuringRead);

  if (
    collection.startedAt !== observedAt ||
    collection.endedAt < collection.startedAt ||
    collection.endedAt - collection.startedAt >
      MAX_OBSERVATION_WINDOW_MS
  ) {
    invalid();
  }

  const fields = observation.fields;
  exactKeys(fields, [
    'accountInfo',
    'getContextUsageSummary',
    'listPermissionRules',
    'hostBefore',
    'hostAfter',
  ]);

  validateField(fields.accountInfo, collection, {
    source: 'Query.accountInfo',
    freshness: 'initialization-cache',
    validateValue: validateAccount,
  });

  validateField(fields.getContextUsageSummary, collection, {
    source: 'Query.getContextUsage(summary)',
    freshness: 'query-report; freshness unproven',
    validateValue: value => text(value),
  });

  validateField(fields.listPermissionRules, collection, {
    source: 'Query.listPermissionRules',
    freshness: 'query-report; permission coverage partial',
    validateValue: validateRules,
  });

  const hostDescriptor = {
    source: 'Desktop manager projection',
    freshness:
      'manager-snapshot; spawn and event values are retained',
    validateValue: value => validateHost(value, binding),
  };

  validateField(fields.hostBefore, collection, hostDescriptor);
  validateField(fields.hostAfter, collection, hostDescriptor);

  const changed =
    canonical(fields.hostBefore.value) !==
    canonical(fields.hostAfter.value);

  if (collection.hostChangedDuringRead !== changed) invalid();

  if (
    !Array.isArray(observation.unknowns) ||
    observation.unknowns.length !== UNKNOWN_CLAIMS.length ||
    observation.unknowns.some(
      (claim, index) => claim !== UNKNOWN_CLAIMS[index],
    )
  ) {
    invalid();
  }

  return collection;
}

export function inspectProbeSample(
  serialized,
  expectedBinding,
  {
    now = Date.now(),
    afterSequence = 0,
    maximumAgeMs,
  } = {},
) {
  const unknown = reason => ({
    state: 'unknown',
    reason,
    qualification: 'unqualified',
  });

  try {
    if (
      typeof serialized !== 'string' ||
      Buffer.byteLength(serialized, 'utf8') > MAX_SAMPLE_BYTES ||
      !Number.isSafeInteger(now) ||
      now < 0 ||
      !Number.isSafeInteger(afterSequence) ||
      afterSequence < 0 ||
      !Number.isSafeInteger(maximumAgeMs) ||
      maximumAgeMs < 1 ||
      maximumAgeMs > MAX_OBSERVATION_WINDOW_MS
    ) {
      invalid();
    }

    validateBinding(expectedBinding);
    const sample = parseStrictJson(serialized);

    exactKeys(sample, [
      'schema',
      'sequence',
      'observedAt',
      'state',
      'binding',
      'result',
      'failureClass',
      'observation',
    ]);

    if (
      sample.schema !== SAMPLE_SCHEMA ||
      sample.state !== 'unqualified' ||
      !Number.isSafeInteger(sample.sequence) ||
      sample.sequence < 1
    ) {
      invalid();
    }

    timestamp(sample.observedAt);
    validateBinding(sample.binding);

    if (sample.result === 'failed') {
      if (
        !FAILURE_CLASSES.has(sample.failureClass) ||
        sample.observation !== null
      ) {
        invalid();
      }

      return unknown('incomplete-sample');
    }

    if (
      sample.result !== 'complete' ||
      sample.failureClass !== null ||
      sample.observation === null
    ) {
      invalid();
    }

    const collection = validateObservation(
      sample.observation,
      sample.binding,
      sample.observedAt,
    );

    if (
      !BINDING_KEYS.every(
        key => sample.binding[key] === expectedBinding[key],
      )
    ) {
      return unknown('binding-mismatch');
    }

    if (now < collection.endedAt) {
      return unknown('clock-before-observation');
    }

    if (now - collection.endedAt > maximumAgeMs) {
      return unknown('expired');
    }

    if (sample.sequence <= afterSequence) {
      return unknown('not-newer');
    }

    return {
      state: 'usable-partial',
      qualification: 'unqualified',
      sample,
    };
  } catch {
    return unknown('invalid-sample');
  }
}
