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
function assess(input = {}) {
  return Object.fromEntries(['binding', 'account', 'model', 'rules', 'host'].map(key => {
    const item = input[key] ?? { state: 'unassessed', basis: 'No dependency assessment supplied.' };
    if (!['unassessed', 'carried-forward', 'compatible', 'incompatible'].includes(item.state)) throw new Error('invalid assessment');
    return [key, { state: item.state, basis: text(item.basis) }];
  }));
}
function projectHost(host, generation) {
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
        if (compatibility.host.state === 'incompatible') return { state: 'unavailable', reason: 'incompatible-dependency',
          source: 'Desktop manager projection', startedAt: began, endedAt: now(), completeness: 'missing' };
        try { return observed(projectHost(record.host, binding.generation), 'Desktop manager projection',
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
export function inspectEnvelope(serialized, expectedBinding, { now = Date.now(), afterSequence = 0 } = {}) {
  const unknown = reason => ({ state: 'unknown', reason, qualification: 'unqualified' });
  try {
    validateBinding(expectedBinding);
    number(now);
    if (!Number.isSafeInteger(afterSequence) || afterSequence < 0 || typeof serialized !== 'string' || serialized.length > 1000000) throw new Error();
    const e = JSON.parse(serialized);
    validateBinding(e.binding);
    if (e.schema !== SCHEMA || e.qualification !== 'unqualified' || e.adapter !== 'synthetic-observer-v1' ||
      e.build !== 'synthetic-fixture' || !Number.isSafeInteger(e.sequence) || e.sequence < 1 ||
      !Array.isArray(e.gaps) || e.gaps.length !== GAPS.length || !GAPS.every(gap => e.gaps.includes(gap))) throw new Error();
    if (canonical(assess(e.compatibility)) !== canonical(e.compatibility)) throw new Error();
    const c = e.collection;
    for (const key of ['startedAt', 'endedAt', 'expiresAt']) number(c[key]);
    if (c.startedAt > c.endedAt || c.expiresAt <= c.endedAt || c.expiresAt - c.endedAt > 60000 ||
      !['collected', 'unavailable', 'discarded'].includes(c.state)) throw new Error();
    if (!e.fields || typeof e.fields !== 'object' || Array.isArray(e.fields)) throw new Error();
    const keys = ['account', 'model', 'rules', 'hostBefore', 'hostAfter'];
    if (c.state !== 'collected') {
      if (Object.keys(e.fields).length) throw new Error();
      text(c.reason);
    } else {
      if (Object.keys(e.fields).length !== keys.length) throw new Error();
      for (const key of keys) {
        const field = e.fields[key];
        number(field.startedAt); number(field.endedAt); text(field.source);
        if (field.startedAt < c.startedAt || field.endedAt < field.startedAt || field.endedAt > c.endedAt) throw new Error();
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
          if (canonical(projectHost(host, e.binding.generation)) !== canonical(value)) throw new Error();
        }
      }
    }
    if (!sameBinding(e.binding, expectedBinding)) return unknown('binding-mismatch');
    if (now < c.endedAt) return unknown('clock-before-observation');
    if (now >= c.expiresAt) return unknown('expired');
    if (e.sequence <= afterSequence) return unknown('not-newer');
    if (c.state !== 'collected') return unknown(c.reason);
    return { state: 'usable-partial', qualification: 'unqualified', envelope: e };
  } catch { return unknown('invalid-envelope'); }
}
