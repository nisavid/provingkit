// Throwaway observer prototype. All callers in this directory use synthetic state.
const SCHEMA = 'desktop-observer.prototype.v1';
const GAPS = ['current-account-route', 'current-model-freshness', 'current-permission-mode',
  'complete-applied-permissions', 'current-cwd', 'native-address-binding', 'external-delivery-and-ack'];
const canonical = value => JSON.stringify(value, function (_key, item) {
  return item && typeof item === 'object' && !Array.isArray(item)
    ? Object.fromEntries(Object.keys(item).sort().map(key => [key, item[key]])) : item;
});
const sameBinding = (record, binding) => record &&
  ['taskId', 'codeSessionId', 'appStartId', 'generation'].every(key => record[key] === binding[key]);
const observed = (value, source, freshness, startedAt, endedAt) => ({
  state: 'observed', value, source, freshness, startedAt, endedAt, completeness: 'partial',
});
const text = value => { if (typeof value !== 'string' || !value) throw new Error('missing string'); return value; };
const boolean = value => { if (typeof value !== 'boolean') throw new Error('missing boolean'); return value; };
const strings = values => values === undefined ? null : Array.from(values, text);
const number = value => { if (!Number.isFinite(value) || value < 0) throw new Error('invalid number'); return value; };
function validateBinding(binding) {
  for (const key of ['taskId', 'codeSessionId', 'appStartId']) text(binding[key]);
  if (!Number.isSafeInteger(binding.generation) || binding.generation < 1) throw new Error('invalid generation');
}
function exactKeys(value, keys) {
  if (!value || typeof value !== 'object' || Array.isArray(value) ||
    canonical(Object.keys(value).sort()) !== canonical([...keys].sort())) throw new Error('invalid keys');
}
const UNASSESSED = { state: 'unassessed', basis: 'No dependency assessment supplied.' };
const HOST_PARTS = {
  spawnAccount: ['spawnRoute'], permissionMode: ['permissionMode', 'modeEvent', 'modeRequestsInFlight'],
  cwd: ['harnessCwd'], pendingChanges: ['sessionPermissionUpdates', 'flagScopeSyncPending'],
  hostGrants: ['alwaysAllowedReasons', 'cuAllowedApps', 'cuGrantFlags', 'effectiveCuAllowedApps', 'effectiveCuGrantFlags'],
};
function assessment(item = UNASSESSED) {
  exactKeys(item, ['state', 'basis']);
  if (!['unassessed', 'carried-forward', 'compatible', 'incompatible'].includes(item.state)) throw new Error('invalid assessment');
  return { state: item.state, basis: text(item.basis) };
}
function assess(input = {}) {
  const keys = ['binding', 'account', 'model', 'rules', ...Object.keys(HOST_PARTS), 'export'];
  if (Object.keys(input).some(key => !keys.includes(key))) throw new Error('unknown dependency');
  return Object.fromEntries(keys.map(key => [key, assessment(input[key])]));
}
function projectHost(input, generation, compatibility) {
  const host = {};
  for (const [dependency, keys] of Object.entries(HOST_PARTS))
    if (compatibility[dependency].state !== 'incompatible') for (const key of keys) host[key] = input[key];
  const flags = values => values === undefined ? null : Object.fromEntries(
    ['clipboardRead', 'clipboardWrite', 'systemKeyCombos'].filter(key => values[key] !== undefined)
      .map(key => [key, boolean(values[key])]));
  const apps = values => values === undefined ? null : values.map(({ bundleId, grantedAt }) =>
    ({ bundleId: text(bundleId), grantedAt: number(grantedAt) }));
  return {
    spawnRoute: host.spawnRoute ? { accountUuid: text(host.spawnRoute.accountUuid), orgId: text(host.spawnRoute.orgId) } : null,
    permissionMode: host.permissionMode === undefined ? null : text(host.permissionMode),
    modeEvent: host.modeEvent?.generation === generation ? {
      mode: text(host.modeEvent.mode), at: number(host.modeEvent.at), generation,
    } : null,
    harnessCwd: host.harnessCwd === undefined ? null : text(host.harnessCwd),
    cwdEventProvenance: 'unavailable',
    alwaysAllowedReasons: strings(host.alwaysAllowedReasons),
    cuAllowedApps: apps(host.cuAllowedApps), cuGrantFlags: flags(host.cuGrantFlags),
    effectiveCuAllowedApps: apps(host.effectiveCuAllowedApps), effectiveCuGrantFlags: flags(host.effectiveCuGrantFlags),
    sessionPermissionUpdateTypes: host.sessionPermissionUpdates?.map(update => text(update.type)) ?? null,
    flagScopeSyncPending: host.flagScopeSyncPending === undefined ? null : boolean(host.flagScopeSyncPending),
    modeRequestsInFlight: Number.isSafeInteger(host.modeRequestsInFlight) && host.modeRequestsInFlight >= 0 ? host.modeRequestsInFlight : null,
    pendingCoverage: 'unknown',
  };
}
function projectRules({ state }) {
  return {
    rules: state.rules.map(({ behavior, source, rule, editability, notInEffect }) => ({
      behavior: text(behavior), source: text(source), rule: text(rule), editability: text(editability),
      ...(notInEffect === undefined ? {} : { notInEffect: boolean(notInEffect) }),
    })),
    workspaceDirectories: state.workspaceDirectories.map(({ path, source }) => ({ path: text(path), source: text(source) })),
    originalCwd: text(state.originalCwd), managedOnly: boolean(state.managedOnly),
    settingsErrorCount: state.errors === undefined ? 0 :
      Array.isArray(state.errors) ? state.errors.length : (() => { throw new Error('invalid errors'); })(),
  };
}

export function createObserver({ selectReceiver, now = Date.now }) {
  let sequence = 0;
  function read(call, project, source, freshness, deadline, assessment) {
    const startedAt = now();
    if (assessment.state === 'incompatible') return { state: 'unavailable', reason: 'incompatible-dependency',
      source, startedAt, endedAt: now(), completeness: 'missing' };
    return new Promise(resolve => {
      let settled = false;
      const finish = result => { if (!settled) { settled = true; clearTimeout(timer); resolve(result); } };
      const timer = setTimeout(() => finish({ state: 'unknown', reason: 'deadline', source,
        startedAt, endedAt: now(), completeness: 'missing' }), Math.max(0, deadline - now()));
      Promise.resolve().then(call).then(value => {
        if (settled) return;
        if (now() >= deadline) return finish({ state: 'unknown', reason: 'deadline', source,
          startedAt, endedAt: now(), completeness: 'missing' });
        try { finish(observed(project(value), source, freshness, startedAt, now())); }
        catch { finish({ state: 'unknown', reason: 'malformed-response', source,
          startedAt, endedAt: now(), completeness: 'missing' }); }
      }).catch(error => finish({ state: 'unavailable', reason: /unsupported control|unknown control|unrecognized.*subtype/i.test(error?.message ?? '')
        ? 'unsupported-control' : 'read-failed', source, startedAt, endedAt: now(), completeness: 'missing' }));
    });
  }
  return {
    async observeReceiver(binding, { ttlMs = 30000, timeoutMs = 100, compatibility: inputCompatibility } = {}) {
      binding = Object.fromEntries(['taskId', 'codeSessionId', 'appStartId', 'generation'].map(key => [key, binding[key]]));
      validateBinding(binding);
      if (![ttlMs, timeoutMs].every(value => Number.isFinite(value) && value > 0 && value <= 60000)) throw new Error('invalid collection bounds');
      const compatibility = assess(inputCompatibility);
      const startedAt = now();
      const envelope = {
        schema: SCHEMA, qualification: 'unqualified', binding, sequence: ++sequence, compatibility,
        adapter: 'synthetic-observer-v1', build: 'synthetic-fixture',
        collection: { state: 'unavailable', startedAt }, fields: {}, gaps: [...GAPS],
      };
      const record = compatibility.binding.state === 'incompatible' ? null : selectReceiver(binding.taskId);
      if (!sameBinding(record, binding) || !record.query || record.unavailableReason) {
        const endedAt = now();
        return { ...envelope, collection: { ...envelope.collection, endedAt, expiresAt: endedAt + ttlMs,
          reason: compatibility.binding.state === 'incompatible' ? 'incompatible-binding-dependency' :
            record?.unavailableReason ?? (record?.query ? 'binding-mismatch' : 'no-existing-query') } };
      }
      const query = record.query, inputStream = record.inputStream;
      const hostSnapshot = () => {
        const began = now();
        try { return observed(projectHost(record.host, binding.generation, compatibility), 'Desktop manager projection',
          'manager-snapshot; spawn and event values are retained', began, now()); }
        catch { return { state: 'unknown', reason: 'malformed-host-projection', source: 'Desktop manager projection',
          startedAt: began, endedAt: now(), completeness: 'missing' }; }
      };
      const hostBefore = hostSnapshot();
      const deadline = startedAt + timeoutMs;
      const [account, model, rules] = await Promise.all([
        read(() => query.accountInfo(), value => {
          const projected = {};
          for (const key of ['apiProvider', 'tokenSource']) if (value[key] !== undefined) projected[key] = text(value[key]);
          if (!Object.keys(projected).length) throw new Error('missing account fields');
          return projected;
        },
          'Query.accountInfo', 'initialization-cache', deadline, compatibility.account),
        read(() => query.getContextUsage({ detail: 'summary' }), value => text(value.model),
          'Query.getContextUsage(summary)', 'query-report; freshness unproven', deadline, compatibility.model),
        read(() => query.listPermissionRules(), projectRules,
          'Query.listPermissionRules', 'query-report; permission coverage partial', deadline, compatibility.rules),
      ]);
      const hostAfter = hostSnapshot();
      const endedAt = now();
      if (selectReceiver(binding.taskId) !== record || !sameBinding(record, binding) ||
        record.query !== query || record.inputStream !== inputStream) {
        return { ...envelope, collection: { state: 'discarded', reason: 'binding-changed-during-read',
          startedAt, endedAt, expiresAt: endedAt + ttlMs } };
      }
      return {
        ...envelope,
        collection: { state: 'collected', startedAt, endedAt, expiresAt: endedAt + ttlMs,
          hostChangedDuringRead: hostBefore.state === 'observed' && hostAfter.state === 'observed'
            ? JSON.stringify(hostBefore.value) !== JSON.stringify(hostAfter.value) : null },
        fields: {
          account, model, rules,
          hostBefore, hostAfter,
        },
        gaps: [...GAPS],
      };
    },
  };
}

// Reads synthetic exported bytes. A valid envelope is still partial and unqualified.
export function inspectEnvelope(serialized, expectedBinding, { now = Date.now(), afterSequence = 0,
  readerAssessment = UNASSESSED, exportAssessment } = {}) {
  const unknown = reason => ({ state: 'unknown', reason, qualification: 'unqualified' });
  try {
    validateBinding(expectedBinding);
    const readerCompatibility = assessment(readerAssessment);
    if (readerCompatibility.state === 'incompatible') return unknown('incompatible-reader-dependency');
    if (exportAssessment && assessment(exportAssessment).state === 'incompatible') return unknown('incompatible-export-dependency');
    number(now);
    if (!Number.isSafeInteger(afterSequence) || afterSequence < 0 || typeof serialized !== 'string' || serialized.length > 1000000) throw new Error();
    const envelope = JSON.parse(serialized);
    exactKeys(envelope, ['schema', 'qualification', 'binding', 'sequence', 'compatibility', 'adapter', 'build', 'collection', 'fields', 'gaps']);
    exactKeys(envelope.binding, ['taskId', 'codeSessionId', 'appStartId', 'generation']);
    validateBinding(envelope.binding);
    if (envelope.schema !== SCHEMA || envelope.qualification !== 'unqualified' || envelope.adapter !== 'synthetic-observer-v1' ||
      envelope.build !== 'synthetic-fixture' || !Number.isSafeInteger(envelope.sequence) || envelope.sequence < 1 ||
      !Array.isArray(envelope.gaps) || envelope.gaps.length !== GAPS.length || !GAPS.every(gap => envelope.gaps.includes(gap))) throw new Error();
    if (canonical(assess(envelope.compatibility)) !== canonical(envelope.compatibility)) throw new Error();
    const collection = envelope.collection;
    exactKeys(collection, ['state', 'startedAt', 'endedAt', 'expiresAt', collection.state === 'collected' ? 'hostChangedDuringRead' : 'reason']);
    for (const key of ['startedAt', 'endedAt', 'expiresAt']) number(collection[key]);
    if (collection.startedAt > collection.endedAt || collection.expiresAt <= collection.endedAt || collection.expiresAt - collection.endedAt > 60000 ||
      !['collected', 'unavailable', 'discarded'].includes(collection.state)) throw new Error();
    if (!envelope.fields || typeof envelope.fields !== 'object' || Array.isArray(envelope.fields)) throw new Error();
    const keys = ['account', 'model', 'rules', 'hostBefore', 'hostAfter'];
    if (collection.state !== 'collected') {
      if (Object.keys(envelope.fields).length) throw new Error();
      text(collection.reason);
    } else {
      if (Object.keys(envelope.fields).length !== keys.length) throw new Error();
      for (const key of keys) {
        const field = envelope.fields[key];
        exactKeys(field, ['state', 'source', 'startedAt', 'endedAt', 'completeness',
          ...(field.state === 'observed' ? ['value', 'freshness'] : ['reason'])]);
        number(field.startedAt); number(field.endedAt); text(field.source);
        if (field.startedAt < collection.startedAt || field.endedAt < field.startedAt || field.endedAt > collection.endedAt) throw new Error();
        if (field.state !== 'observed') {
          if (!['unknown', 'unavailable'].includes(field.state) || field.completeness !== 'missing' || 'value' in field) throw new Error();
          text(field.reason); continue;
        }
        if (field.completeness !== 'partial') throw new Error();
        text(field.freshness);
        const value = field.value;
        if (key === 'model') text(value);
        else if (key === 'account') {
          if (!Object.keys(value).length || Object.keys(value).some(k => !['apiProvider', 'tokenSource'].includes(k))) throw new Error();
          Object.values(value).forEach(text);
        } else if (key === 'rules') {
          if (!Number.isSafeInteger(value.settingsErrorCount) || value.settingsErrorCount < 0) throw new Error();
          const projected = { ...projectRules({ state: value }), settingsErrorCount: value.settingsErrorCount };
          if (canonical(projected) !== canonical(value)) throw new Error();
        } else {
          if (value.pendingCoverage !== 'unknown') throw new Error();
          // Null means the adapter has no value; do not coerce it to an empty grant.
          const host = Object.fromEntries(Object.entries(value).filter(([, v]) => v !== null));
          host.sessionPermissionUpdates = host.sessionPermissionUpdateTypes?.map(type => ({ type }));
          if (canonical(projectHost(host, envelope.binding.generation, envelope.compatibility)) !== canonical(value)) throw new Error();
        }
      }
    }
    if (envelope.compatibility.export.state === 'incompatible') return unknown('incompatible-export-dependency');
    if (!sameBinding(envelope.binding, expectedBinding)) return unknown('binding-mismatch');
    if (now < collection.endedAt) return unknown('clock-before-observation');
    if (now >= collection.expiresAt) return unknown('expired');
    if (envelope.sequence <= afterSequence) return unknown('not-newer');
    if (collection.state !== 'collected') return unknown(collection.reason);
    return { state: 'usable-partial', qualification: 'unqualified', readerCompatibility, envelope: envelope };
  } catch { return unknown('invalid-envelope'); }
}
