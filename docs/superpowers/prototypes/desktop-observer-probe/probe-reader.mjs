import {
  BINDING_KEYS,
  FAILURE_CLASSES,
  FAILURE_STAGES,
  FIELD_NAMES,
  GETTER_SET_ID,
  HOST_GAP_FIELDS,
  HOST_KEYS,
  MAX_ARRAY_ITEMS,
  MAX_CWD_BYTES,
  MAX_OBSERVATION_WINDOW_MS,
  MAX_SAMPLE_BYTES,
  MAX_TEXT_BYTES,
  MONOTONIC_CLOCK_ID,
  SAMPLE_SCHEMA,
  isValidLinuxBootId,
  SELECTED_EXECUTOR_REPORT_BASIS,
  SELECTED_EXECUTOR_REPORT_KEYS,
  UNKNOWN_CLAIMS,
} from './observer-contract.mjs';

const MAX_PARSE_DEPTH = 32;
const FAILURE_CLASS_SET = new Set(FAILURE_CLASSES);
const FAILURE_STAGE_SET = new Set(FAILURE_STAGES);
const HOST_GAP_FIELD_SET = new Set(HOST_GAP_FIELDS);

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

  if (
    binding.monotonicClockId !== MONOTONIC_CLOCK_ID ||
    !isValidLinuxBootId(binding.linuxBootId)
  ) {
    invalid();
  }

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
  exactKeys(value, SELECTED_EXECUTOR_REPORT_KEYS);

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
    value.reportBasis !== SELECTED_EXECUTOR_REPORT_BASIS
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

  boundedArray(value.gaps, gap => {
    exactKeys(gap, ['field', 'failureClass']);

    if (
      !HOST_GAP_FIELD_SET.has(gap.field) ||
      !FAILURE_CLASS_SET.has(gap.failureClass)
    ) {
      invalid();
    }
  });

  if (
    new Set(value.gaps.map(gap => gap.field)).size !==
    value.gaps.length
  ) {
    invalid();
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
    'status',
    'failureClass',
    'failureStage',
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

  if (field.status === 'available') {
    if (
      field.failureClass !== null ||
      field.failureStage !== null
    ) {
      invalid();
    }

    validateValue(field.value);
    return;
  }

  if (
    field.status !== 'unavailable' ||
    field.value !== null ||
    !FAILURE_CLASS_SET.has(field.failureClass) ||
    !FAILURE_STAGE_SET.has(field.failureStage)
  ) {
    invalid();
  }
}

function validateObservation(observation, binding, observedAt) {
  exactKeys(observation, ['collection', 'fields', 'unknowns']);

  const collection = observation.collection;
  exactKeys(collection, [
    'startedAt',
    'endedAt',
    'startedAtMonotonicMs',
    'endedAtMonotonicMs',
    'hostChangedDuringRead',
  ]);

  timestamp(collection.startedAt);
  timestamp(collection.endedAt);
  timestamp(collection.startedAtMonotonicMs);
  timestamp(collection.endedAtMonotonicMs);

  if (collection.hostChangedDuringRead !== null) {
    boolean(collection.hostChangedDuringRead);
  }

  if (
    collection.startedAt !== observedAt ||
    collection.endedAt < collection.startedAt ||
    collection.endedAt - collection.startedAt >
      MAX_OBSERVATION_WINDOW_MS
  ) {
    invalid();
  }

  if (
    collection.endedAtMonotonicMs <
      collection.startedAtMonotonicMs ||
    collection.endedAtMonotonicMs -
      collection.startedAtMonotonicMs >
      MAX_OBSERVATION_WINDOW_MS
  ) {
    invalid();
  }

  const fields = observation.fields;
  exactKeys(fields, FIELD_NAMES);

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

  if (
    fields.hostBefore.status === 'available' &&
    fields.hostAfter.status === 'available'
  ) {
    const changed =
      canonical(fields.hostBefore.value) !==
      canonical(fields.hostAfter.value);

    if (collection.hostChangedDuringRead !== changed) invalid();
  } else if (collection.hostChangedDuringRead !== null) {
    invalid();
  }

  if (
    !Array.isArray(observation.unknowns) ||
    observation.unknowns.length !== UNKNOWN_CLAIMS.length ||
    observation.unknowns.some(
      (claim, index) => claim !== UNKNOWN_CLAIMS[index],
    )
  ) {
    invalid();
  }

  const partial = Object.values(fields).some(field =>
    field.status === 'unavailable' ||
    (
      field.status === 'available' &&
      Array.isArray(field.value?.gaps) &&
      field.value.gaps.length > 0
    ),
  );

  return { collection, partial };
}

export function inspectProbeSample(
  serialized,
  expectedBinding,
  {
    now = Date.now(),
    monotonicNow,
    monotonicClockId,
    linuxBootId,
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
      !Number.isSafeInteger(monotonicNow) ||
      monotonicNow < 0 ||
      typeof monotonicClockId !== 'string' ||
      !isValidLinuxBootId(linuxBootId) ||
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
      'observedAtMonotonicMs',
      'state',
      'binding',
      'result',
      'failureClass',
      'failureStage',
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
    timestamp(sample.observedAtMonotonicMs);
    validateBinding(sample.binding);

    if (
      !BINDING_KEYS.every(
        key => sample.binding[key] === expectedBinding[key],
      )
    ) {
      return unknown('binding-mismatch');
    }

    if (
      monotonicClockId !== sample.binding.monotonicClockId ||
      linuxBootId !== sample.binding.linuxBootId
    ) {
      return unknown('incomparable-clock');
    }

    if (sample.sequence <= afterSequence) {
      return unknown('not-newer');
    }

    if (now < sample.observedAt) {
      return unknown('clock-before-observation');
    }

    if (monotonicNow < sample.observedAtMonotonicMs) {
      return unknown('monotonic-clock-before-observation');
    }

    if (
      now - sample.observedAt > maximumAgeMs ||
      monotonicNow - sample.observedAtMonotonicMs >
        maximumAgeMs
    ) {
      return unknown('expired');
    }

    if (sample.result === 'failed') {
      if (
        !FAILURE_CLASS_SET.has(sample.failureClass) ||
        !FAILURE_STAGE_SET.has(sample.failureStage) ||
        sample.observation !== null
      ) {
        invalid();
      }

      return unknown('incomplete-sample');
    }

    if (
      (
        sample.result !== 'complete' &&
        sample.result !== 'partial'
      ) ||
      sample.failureClass !== null ||
      sample.failureStage !== null ||
      sample.observation === null
    ) {
      invalid();
    }

    const { collection, partial } = validateObservation(
      sample.observation,
      sample.binding,
      sample.observedAt,
    );

    if (
      (sample.result === 'partial') !== partial
    ) {
      invalid();
    }

    if (
      collection.startedAtMonotonicMs !==
      sample.observedAtMonotonicMs
    ) {
      invalid();
    }

    if (now < collection.endedAt) {
      return unknown('clock-before-observation');
    }

    if (monotonicNow < collection.endedAtMonotonicMs) {
      return unknown('monotonic-clock-before-observation');
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
